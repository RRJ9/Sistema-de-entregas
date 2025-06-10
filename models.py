from sqlalchemy import Column, Integer, String, Date, ForeignKey
from database import Base

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    correo = Column(String)
    telefono = Column(String)
    direccion = Column(String)
    ciudad = Column(String)
    codigo_postal = Column(String)

class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    id_cliente = Column(Integer, ForeignKey("clientes.id"))
    fecha_pedido = Column(Date)
    descripcion = Column(String)
    estado = Column(String)

class Entrega(Base):
    __tablename__ = "entregas"
    id = Column(Integer, primary_key=True, index=True)
    id_pedido = Column(Integer, ForeignKey("pedidos.id"))
    fecha_entrega = Column(Date)
    estado = Column(String)

class PedidoItem(Base):
    __tablename__ = "pedido_items"
    id = Column(Integer, primary_key=True, index=True)
    id_pedido = Column(Integer, ForeignKey("pedidos.id"))
    descripcion_producto = Column(String, nullable=False)
    cantidad = Column(Integer, nullable=False)