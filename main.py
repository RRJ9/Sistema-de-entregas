from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import models
import schemas
import database
from fastapi import Query
from typing import Optional
from models import *
from datetime import datetime, timedelta
from sqlalchemy import func
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import UploadFile, File, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import re
from twilio.rest import Client
import os



router = APIRouter()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router) 


# Dependencia para sesión DB
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/pedidos")
def crear_pedido(pedido: schemas.PedidoCreate, db: Session = Depends(get_db)):
    nuevo = models.Pedido(**pedido.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@app.get("/entregas/pendientes", response_model=list[schemas.EntregaOut])
def listar_entregas_pendientes(db: Session = Depends(get_db)):
    return db.query(models.Entrega).filter(models.Entrega.estado == "pendiente").all()

@app.post("/entregas")
def crear_entrega(entrega: schemas.EntregaCreate, db: Session = Depends(get_db)):
    nueva_entrega = models.Entrega(**entrega.dict())
    db.add(nueva_entrega)
    db.commit()
    db.refresh(nueva_entrega)
    # Obtener cliente
    pedido = db.query(models.Pedido).filter(models.Pedido.id == nueva_entrega.id_pedido).first()
    cliente = db.query(models.Cliente).filter(models.Cliente.id == pedido.id_cliente).first()

    # Calcular rango basado en "hoy"
    hoy = datetime.today().date()

    fecha_min_date = hoy + timedelta(days=1)
    fecha_max_date = hoy + timedelta(days=3)

    fecha_min = fecha_min_date.strftime("%Y-%m-%d")
    fecha_max = fecha_max_date.strftime("%Y-%m-%d")

    # Enviar correo
    enviar_correo_entrega(cliente.correo, cliente.nombre, fecha_min, fecha_max)


    return nueva_entrega

@app.put("/entregas/{entrega_id}")
def actualizar_entrega(entrega_id: int, entrega_update: schemas.EntregaUpdate, db: Session = Depends(get_db)):
    entrega = db.query(models.Entrega).filter(models.Entrega.id == entrega_id).first()

    if not entrega:
        return {"error": "Entrega no encontrada"}

    # Actualizar campos si se proporcionan
    if entrega_update.fecha_entrega is not None:
        entrega.fecha_entrega = entrega_update.fecha_entrega
    if entrega_update.estado is not None:
        entrega.estado = entrega_update.estado

    db.commit()
    db.refresh(entrega)
    return entrega

@app.get("/pedidos", response_model=list[schemas.PedidoOut])
def listar_pedidos(db: Session = Depends(get_db)):
    return db.query(models.Pedido).all()

@app.get("/clientes", response_model=list[schemas.ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(models.Cliente).all()

@app.delete("/entregas/{entrega_id}")
def eliminar_entrega(entrega_id: int, db: Session = Depends(get_db)):
    entrega = db.query(models.Entrega).filter(models.Entrega.id == entrega_id).first()

    if not entrega:
        return {"error": "Entrega no encontrada"}

    db.delete(entrega)
    db.commit()
    return {"mensaje": f"Entrega con ID {entrega_id} eliminada correctamente."}

@app.get("/entregas/calendar")
def entregas_calendar(estado: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Entrega, models.Pedido, models.Cliente)\
        .join(models.Pedido, models.Entrega.id_pedido == models.Pedido.id)\
        .outerjoin(models.Cliente, models.Pedido.id_cliente == models.Cliente.id)

    if estado:
        query = query.filter(models.Entrega.estado == estado)

    resultados = query.all()

    eventos = []
    for entrega, pedido, cliente in resultados:
        if entrega.fecha_entrega is None:
            continue

        color = "#f1c40f"  # pendiente
        if entrega.estado == "entregado":
            color = "#2ecc71"
        elif entrega.estado == "reagendado":
            color = "#9b59b6"
        elif entrega.estado == "en_camino":
            color = "#2980b9"

        nombre_cliente = cliente.nombre if cliente else "Cliente desconocido"

        evento = {
            "id": entrega.id,
            "title": f"Pedido {pedido.id} - Cliente: {nombre_cliente}",
            "start": entrega.fecha_entrega.strftime("%Y-%m-%d"),
            "color": color,
            "allDay": True,
            "extendedProps": {
                "estado": entrega.estado,
                "direccion": cliente.direccion if cliente else "Sin dirección",
                "telefono": cliente.telefono if cliente else "Sin teléfono",
                "notas": pedido.descripcion if pedido.descripcion else "",
                "id_pedido_original": pedido.id
            }
        }
        eventos.append(evento)

    return eventos


# 🚚 POST /pedido_items → agregar producto a pedido
@app.post("/pedido_items", response_model=schemas.PedidoItemOut)
def crear_pedido_item(item: schemas.PedidoItemCreate, db: Session = Depends(get_db)):
    nuevo_item = models.PedidoItem(**item.dict())
    db.add(nuevo_item)
    db.commit()
    db.refresh(nuevo_item)
    return nuevo_item

# 🚚 GET /pedido_items → listar productos de un pedido
@app.get("/pedido_items", response_model=list[schemas.PedidoItemOut])
def listar_pedido_items(id_pedido: int, db: Session = Depends(get_db)):
    return db.query(models.PedidoItem).filter(models.PedidoItem.id_pedido == id_pedido).all()

@app.get("/pedidos/pendientes_count")
def pedidos_pendientes_count(db: Session = Depends(get_db)):
    subquery = db.query(models.Entrega.id_pedido).distinct()
    count = db.query(models.Pedido).filter(
        models.Pedido.estado == "pendiente",
        ~models.Pedido.id.in_(subquery)
    ).count()
    return {"pendientes": count}

@app.delete("/pedido_items/{item_id}")
def eliminar_pedido_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.PedidoItem).filter(models.PedidoItem.id == item_id).first()
    
    if not item:
        return {"error": "Producto no encontrado"}
    
    db.delete(item)
    db.commit()
    
    return {"mensaje": f"Producto con ID {item_id} eliminado correctamente."}

@app.get("/pedidos/sin_entrega")
def pedidos_sin_entrega(db: Session = Depends(get_db)):
    subquery = db.query(models.Entrega.id_pedido).distinct()
    pedidos = db.query(models.Pedido, models.Cliente)\
        .join(models.Cliente, models.Pedido.id_cliente == models.Cliente.id)\
        .filter(~models.Pedido.id.in_(subquery))\
        .order_by(models.Pedido.fecha_pedido.asc())\
        .all()

    resultado = []
    for pedido, cliente in pedidos:
        resultado.append({
            "id_pedido": pedido.id,
            "cliente": cliente.nombre,
            "fecha_pedido": pedido.fecha_pedido.strftime("%Y-%m-%d") if pedido.fecha_pedido else "",
            "estado": pedido.estado,
            "descripcion": pedido.descripcion
        })
    return resultado


@app.post("/clientes")
def crear_cliente(cliente: schemas.ClienteCreate, db: Session = Depends(get_db)):
    nuevo_cliente = models.Cliente(
        nombre=cliente.nombre,
        correo=cliente.correo,
        telefono=cliente.telefono,
        direccion=cliente.direccion,
        ciudad=cliente.ciudad,
        codigo_postal=cliente.codigo_postal
    )
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    return nuevo_cliente

@app.get("/entregas/detalle_dia")
def get_entregas_detalle_dia(fecha: str, db: Session = Depends(get_db)):
    # Obtener entregas para esa fecha
    entregas = db.query(Entrega).filter(Entrega.fecha_entrega == fecha).all()

    resultado = []

    for entrega in entregas:
        # Obtener el pedido relacionado
        pedido = db.query(Pedido).filter(Pedido.id == entrega.id_pedido).first()
        cliente = db.query(Cliente).filter(Cliente.id == pedido.id_cliente).first()

        # Obtener los productos del pedido
        productos_query = db.query(PedidoItem).filter(PedidoItem.id_pedido == pedido.id).all()
        productos = [
            {
                "descripcion": item.descripcion_producto,
                "cantidad": item.cantidad,
            }
            for item in productos_query
        ]

        # Armar resultado para esta entrega
        entrega_data = {
            "id_entrega": entrega.id,
            "id_pedido": pedido.id,
            "cliente": cliente.nombre if cliente else "",
            "direccion": cliente.direccion if cliente else "",
            "telefono": cliente.telefono if cliente else "",
            "fecha_entrega": entrega.fecha_entrega.strftime("%Y-%m-%d"),
            "estado": entrega.estado,
            "productos": productos
        }

        resultado.append(entrega_data)

    return resultado

@app.get("/estadisticas/logistica")
def estadisticas_logistica(db: Session = Depends(get_db)):
    hoy = datetime.today().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # lunes de esta semana

    # Entregas pendientes para hoy
    pendientes_hoy = db.query(Entrega).filter(
        Entrega.fecha_entrega == hoy,
        Entrega.estado != 'entregado'
    ).count()

    # Entregas pendientes para esta semana
    pendientes_semana = db.query(Entrega).filter(
        Entrega.fecha_entrega >= inicio_semana,
        Entrega.fecha_entrega <= hoy + timedelta(days=6 - hoy.weekday()),
        Entrega.estado != 'entregado'
    ).count()

    # Total entregas pendientes
    total_pendientes = db.query(Entrega).filter(
        Entrega.estado != 'entregado'
    ).count()

    return {
        "hoy": pendientes_hoy,
        "semana": pendientes_semana,
        "total": total_pendientes
    }


@app.get("/estadisticas/ventas")
def estadisticas_ventas(db: Session = Depends(get_db)):
    resultados = db.query(
        Pedido.descripcion.label("vendedor"),  # campo temporal para probar los gráficos
        func.count(Pedido.id).label("total")
    ).filter(
        Pedido.estado == 'pendiente'
    ).group_by(
        Pedido.descripcion
    ).all()

    vendedores = [row.vendedor for row in resultados]
    pedidos = [row.total for row in resultados]

    return {
        "vendedores": vendedores,
        "pedidos": pedidos
    }


def enviar_correo_entrega(destinatario_email, destinatario_nombre, fecha_min, fecha_max):
    remitente_email = "radiorefrigeraciondejuarez9@gmail.com"
    remitente_password = "fiixgspfealrklja"  

    # Crear mensaje
    msg = MIMEMultipart()
    msg['From'] = remitente_email
    msg['To'] = destinatario_email
    msg['Subject'] = "Confirmación de entrega programada"

    # Cuerpo del mensaje
    cuerpo = f"""
    Estimado/a {destinatario_nombre},

    Le informamos que su pedido ha sido programado para entrega en el siguiente rango de fechas:

    ENTRE EL {fecha_min} Y EL {fecha_max}.

    No es necesario que esté pendiente en un día específico, nuestro equipo le contactará cuando su pedido esté en camino.

    Gracias por su preferencia.

    Atentamente,
    Radio Refrigeración de Juárez
    """

    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        # Conexión SMTP con Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente_email, remitente_password)
        server.send_message(msg)
        server.quit()

        print(f"Correo enviado a {destinatario_email}")

    except Exception as e:
        print(f"Error al enviar correo: {e}")

@app.post("/entregas")
def crear_entrega(entrega: schemas.EntregaCreate, db: Session = Depends(get_db)):
    nueva_entrega = models.Entrega(**entrega.dict())
    db.add(nueva_entrega)
    db.commit()
    db.refresh(nueva_entrega)

    # Obtener cliente
    pedido = db.query(models.Pedido).filter(models.Pedido.id == nueva_entrega.id_pedido).first()
    cliente = db.query(models.Cliente).filter(models.Cliente.id == pedido.id_cliente).first()

    # Calcular rango
    fecha_min = nueva_entrega.fecha_entrega.strftime("%Y-%m-%d")
    fecha_max_date = nueva_entrega.fecha_entrega + timedelta(days=2)
    fecha_max = fecha_max_date.strftime("%Y-%m-%d")

    # Enviar correo
    enviar_correo_entrega(cliente.correo, cliente.nombre, fecha_min, fecha_max)

    return nueva_entrega

@app.post("/extraer_articulos_factura")
def extraer_articulos_factura(archivo: UploadFile = File(...)):
    productos = []

    def insertar_espacios_descripcion(texto):
        texto = re.sub(r'(?<=\d)(?=[A-Z])', ' ', texto)
        texto = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', texto)
        texto = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', texto)
        texto = re.sub(r'(?<=[A-Z])(?=\d)', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()

    with pdfplumber.open(archivo.file) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            print("📝 TEXTO COMPLETO:\n", texto)

            lineas = texto.split('\n')
            for linea in lineas:
                match = re.match(r"^(\d+\.\d+)\s+([A-Z0-9]+)\s+[A-Z]\s+[A-Z0-9]+\s+(\d+)\s+(.+?)\s+[\d,]+\.\d+\s+[\d,]+\.\d+$", linea)
                if match:
                    cantidad = match.group(1)
                    codigo = match.group(2)
                    clave_sat = match.group(3)
                    descripcion_cruda = match.group(4)
                    descripcion = insertar_espacios_descripcion(descripcion_cruda)

                    productos.append({
                        "cantidad": int(float(cantidad)),
                        "codigo": codigo,
                        "clave_sat": clave_sat,
                        "descripcion": descripcion
                    })
                    print("✅ Detectado producto:", productos[-1])

    return productos

@app.get("/ping")
def ping():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)