from pydantic import BaseModel
from datetime import date
from typing import Optional

class PedidoCreate(BaseModel):
    id_cliente: int
    fecha_pedido: date
    descripcion: Optional[str]
    estado: Optional[str]

class EntregaOut(BaseModel):
    id: int
    id_pedido: int
    fecha_entrega: Optional[date]
    estado: str

    class Config:
        from_attributes = True

class EntregaCreate(BaseModel):
    id_pedido: int
    fecha_entrega: Optional[date] = None
    estado: Optional[str] = "pendiente"

    class Config:
        from_attributes = True

class EntregaUpdate(BaseModel):
    fecha_entrega: Optional[date] = None
    estado: Optional[str] = None

    class Config:
        from_attributes = True

class PedidoOut(BaseModel):
    id: int
    id_cliente: int
    fecha_pedido: Optional[date]
    descripcion: Optional[str]
    estado: str

    class Config:
        from_attributes = True       

class ClienteOut(BaseModel):
    id: int
    nombre: str
    correo: str
    telefono: Optional[str]
    direccion: Optional[str]
    ciudad: Optional[str]
    codigo_postal: Optional[str]

    class Config:
        from_attributes = True

# PedidoItem - CREATE
class PedidoItemCreate(BaseModel):
    id_pedido: int
    descripcion_producto: str
    cantidad: int

# PedidoItem - OUT
class PedidoItemOut(BaseModel):
    id: int
    id_pedido: int
    descripcion_producto: str
    cantidad: int

    class Config:
        orm_mode = True

class ClienteCreate(BaseModel):
    nombre: str
    correo: str
    telefono: str
    direccion: str
    ciudad: str
    codigo_postal: str

    class Config:
        from_attributes = True