# ecommerce-flask/database.py

from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash

# --- Configuración de la Conexión a MongoDB ---
client = MongoClient('mongodb://localhost:27017/')
db = client['ecommerce']


# --- Función para mapear el campo _id a id ---
def _mapear_id(documento):
    if documento and '_id' in documento:
        documento['id'] = str(documento['_id'])
    return documento

# --- Funciones de Usuario ---
def obtener_usuario_por_correo(correo):
    """Busca un usuario por su correo electrónico."""
    usuario = db.usuarios.find_one({'correo': correo})
    return _mapear_id(usuario)

def obtener_usuario_por_id(usuario_id):
    try:
        usuario = db.usuarios.find_one({'_id': ObjectId(usuario_id)})
        return _mapear_id(usuario)
    except Exception:
        return None


# -- Función para crear un nuevo usuario ---
def crear_usuario(nombre, correo, password):
    """Crea un nuevo usuario con contraseña hasheada y rol de cliente."""
    usuario = {
        "nombre": nombre,
        "correo": correo,
        "password": generate_password_hash(password),
        "rol": "cliente"  # Todos los nuevos usuarios son clientes por defecto
    }
    db.usuarios.insert_one(usuario)
    return usuario

def obtener_usuarios():
    usuarios_cursor = db.usuarios.find()
    return [_mapear_id(user) for user in usuarios_cursor]

################################################################################################################
# --- Funciones de Producto y Categoría ---

def obtener_categorias():
    """
    Devuelve todas las categorías disponibles.
    """
    categorias_cursor = db.categorias.find()
    return [_mapear_id(cat) for cat in categorias_cursor]


def obtener_categoria_por_id(categoria_id):
    """
    Devuelve una categoría específica por su ObjectId.
    """
    try:
        categoria = db.categorias.find_one({'_id': ObjectId(categoria_id)})
        return _mapear_id(categoria)
    except Exception:
        return None


def obtener_productos():
    """
    Obtiene todos los productos, junto con el nombre de la categoría asociada.
    Usado tanto por la tienda (usuarios) como por el CRUD del administrador.
    """
    pipeline = [
        {
            '$lookup': {
                'from': 'categorias',
                'localField': 'categoria',     # <- referencia a ObjectId
                'foreignField': '_id',
                'as': 'categoria_info'
            }
        },
        {
            '$unwind': {
                'path': '$categoria_info',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$project': {
                'nombre': 1,
                'descripcion': 1,
                'precio': 1,
                'inventario': 1,
                'activo': 1,
                'categoria_id': '$categoria_info._id',
                'categoria_nombre': '$categoria_info.nombre'
            }
        }
    ]

    productos_cursor = db.productos.aggregate(pipeline)
    return [_mapear_id(prod) for prod in productos_cursor]


def obtener_productos_por_categoria(categoria_id):
    """
    Devuelve productos que pertenecen a una categoría específica (por ObjectId),
    junto con el nombre de la categoría.
    Usado por la tienda cuando el usuario filtra productos.
    """
    try:
        pipeline = [
            {'$match': {'categoria': ObjectId(categoria_id)}},
            {
                '$lookup': {
                    'from': 'categorias',
                    'localField': 'categoria',
                    'foreignField': '_id',
                    'as': 'categoria_info'
                }
            },
            {'$unwind': {'path': '$categoria_info', 'preserveNullAndEmptyArrays': True}},
            {
                '$project': {
                    'nombre': 1,
                    'descripcion': 1,
                    'precio': 1,
                    'inventario': 1,
                    'activo': 1,
                    'categoria_id': '$categoria_info._id',
                    'categoria_nombre': '$categoria_info.nombre'
                }
            }
        ]

        productos_cursor = db.productos.aggregate(pipeline)
        return [_mapear_id(prod) for prod in productos_cursor]
    except Exception:
        return []


def obtener_producto_por_id(documento):
    """
    Obtiene un producto específico junto con el nombre y el ID de su categoría.
    Usado tanto para editar un producto (admin) como para mostrar detalle (usuario).
    """
    try:
        pipeline = [
            {'$match': {'_id': ObjectId(documento)}},
            {
                '$lookup': {
                    'from': 'categorias',
                    'localField': 'categoria',
                    'foreignField': '_id',
                    'as': 'categoria_info'
                }
            },
            {'$unwind': {'path': '$categoria_info', 'preserveNullAndEmptyArrays': True}},
            {
                '$project': {
                    'nombre': 1,
                    'descripcion': 1,
                    'precio': 1,
                    'inventario': 1,
                    'activo': 1,
                    'categoria_id': '$categoria_info._id',
                    'categoria_nombre': '$categoria_info.nombre'
                }
            }
        ]

        producto = list(db.productos.aggregate(pipeline))
        return _mapear_id(producto[0]) if producto else None
    except Exception:
        return None

def obtener_reseñas():
    reseñas_cursor = db.reseñas.find()
    return [_mapear_id(res) for res in reseñas_cursor]

def crear_reseña(producto_id, usuario_id, calificacion, comentario):
    reseña = {
        "producto_id": producto_id,
        "usuario_id": usuario_id,
        "calificacion": calificacion,
        "comentario": comentario
    }
    db.reseñas.insert_one(reseña)
    return reseña

def eliminar_reseña(reseña_id):
    try:
        resultado = db.reseñas.delete_one({'_id': ObjectId(reseña_id)})
        return resultado.deleted_count > 0
    except Exception:
        return False

# --- Funciones de Carrito ---    
def obtener_carrito_por_usuario(usuario_id):
    """
    Obtiene los productos en el carrito de un usuario y calcula el total.
    Usa ObjectId tanto para usuario como para productos.
    """
    # Asegurar tipo ObjectId
    if isinstance(usuario_id, str):
        usuario_id = ObjectId(usuario_id)

    # Buscar primero si el carrito existe
    carrito = db.carrito.find_one({'usuario_id': usuario_id})
    if not carrito or not carrito.get('productos'):
        return {'items': [], 'total': 0}

    # Pipeline de agregación para unir con los productos
    pipeline = [
        {'$match': {'usuario_id': usuario_id}},
        {'$unwind': '$productos'},
        {
            '$lookup': {
                'from': 'productos',
                'localField': 'productos',
                'foreignField': '_id',
                'as': 'producto_info'
            }
        },
        {'$unwind': '$producto_info'},
        {
            '$group': {
                '_id': '$producto_info._id',
                'nombre': {'$first': '$producto_info.nombre'},
                'precio': {'$first': '$producto_info.precio'},
                'cantidad': {'$sum': 1},
                'subtotal': {'$sum': '$producto_info.precio'}
            }
        },
        {
            '$project': {
                'producto_id': '$_id',
                'nombre': 1,
                'precio': 1,
                'cantidad': 1,
                'subtotal': 1
            }
        }
    ]

    items = list(db.carrito.aggregate(pipeline))
    total = sum(item.get('subtotal', 0) for item in items)

    # Actualizar total en la base de datos
    db.carrito.update_one(
        {'usuario_id': usuario_id},
        {'$set': {'total': total}},
        upsert=True
    )

    return {'items': items, 'total': total}


def agregar_producto_al_carrito_db(usuario_id, producto_object_id):
    """Agrega un producto al carrito de un usuario en la BD."""
    if isinstance(usuario_id, str):
        usuario_id = ObjectId(usuario_id)
    if isinstance(producto_object_id, str):
        producto_object_id = ObjectId(producto_object_id)

    db.carrito.update_one(
        {'usuario_id': usuario_id},
        {'$push': {'productos': ObjectId(producto_object_id)}},
        
        upsert=True  # Crea el carrito si no existe
    )

def vaciar_carrito_db(usuario_id):
    """Vacía el carrito de un usuario en la BD (establece el array de productos a vacío)."""
    if isinstance(usuario_id, str):
        usuario_id = ObjectId(usuario_id)
    
    db.carrito.update_one(
        {'usuario_id': usuario_id},
        {'$set': {'productos': [], 'total': 0}}    #MEDIA HORA VIENDO POR QUE NO JALABA Y TENIA ESCRITO MAL EL NOMBRE DEL CAMPO
    )

# --- Funciones de Pedidos ---
def obtener_todos_los_pedidos():
    """Obtiene todos los pedidos en la base de datos."""
    pedidos_cursor = db.pedidos.find().sort('fecha', -1)
    return [_mapear_id(pedido) for pedido in pedidos_cursor]

def crear_pedido(usuario_id, items_carrito, total):
    """Crea un nuevo pedido con los productos del carrito."""
    from datetime import datetime
    import pytz
    
    # Usar timezone de Ciudad de México
    mexico_tz = pytz.timezone('America/Mexico_City')
    fecha_actual = datetime.now(mexico_tz)
    
    if isinstance(usuario_id, str):
        usuario_id = ObjectId(usuario_id)
    
    pedido = {
        "usuario_id": usuario_id,
        "productos": items_carrito,
        "total": total,
        "fecha": fecha_actual,
        "estado": "pendiente"
    }
    
    resultado = db.pedidos.insert_one(pedido)
    return resultado.inserted_id

def obtener_pedidos_por_usuario(usuario_id):
    """Obtiene todos los pedidos de un usuario."""
    if isinstance(usuario_id, str):
        usuario_id = ObjectId(usuario_id)
    
    pedidos_cursor = db.pedidos.find({'usuario_id': usuario_id}).sort('fecha', -1)
    return [_mapear_id(pedido) for pedido in pedidos_cursor]

def obtener_pedido_por_id(pedido_id):
    """Obtiene un pedido específico por su ID."""
    try:
        pedido = db.pedidos.find_one({'_id': ObjectId(pedido_id)})
        return _mapear_id(pedido)
    except Exception:
        return None

def reducir_inventario_producto(producto_id, cantidad):
    """Reduce el inventario de un producto específico."""
    try:
        if isinstance(producto_id, str):
            producto_id = ObjectId(producto_id)
        
        resultado = db.productos.update_one(
            {'_id': producto_id},
            {'$inc': {'inventario': -cantidad}}
        )
        return resultado.modified_count > 0
    except Exception:
        return False

def verificar_inventario_suficiente(producto_id, cantidad_solicitada):
    """Verifica si hay suficiente inventario para un producto."""
    try:
        if isinstance(producto_id, str):
            producto_id = ObjectId(producto_id)
        
        producto = db.productos.find_one({'_id': producto_id})
        if producto:
            return producto.get('inventario', 0) >= cantidad_solicitada
        return False
    except Exception:
        return False

def actualizar_estado_pedido(pedido_id, nuevo_estado):
    """Actualiza el estado de un pedido."""
    try:
        if isinstance(pedido_id, str):
            pedido_id = ObjectId(pedido_id)
        
        resultado = db.pedidos.update_one(
            {'_id': pedido_id},
            {'$set': {'estado': nuevo_estado}}
        )
        return resultado.modified_count > 0
    except Exception:
        return False

def obtener_pedidos_con_usuario():
    """Obtiene todos los pedidos con información del usuario para el admin."""
    pipeline = [
        {
            '$lookup': {
                'from': 'usuarios',
                'localField': 'usuario_id',
                'foreignField': '_id',
                'as': 'usuario_info'
            }
        },
        {
            '$unwind': {
                'path': '$usuario_info',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$project': {
                'usuario_id': 1,
                'productos': 1,
                'total': 1,
                'fecha': 1,
                'estado': 1,
                'usuario_nombre': '$usuario_info.nombre',
                'usuario_correo': '$usuario_info.correo'
            }
        },
        {
            '$sort': {'fecha': -1}
        }
    ]
    
    pedidos_cursor = db.pedidos.aggregate(pipeline)
    return [_mapear_id(pedido) for pedido in pedidos_cursor]

def crear_pedido_desde_admin(usuario_id, productos_data, total, estado="pendiente"):
    """Crea un nuevo pedido desde el panel de administración."""
    from datetime import datetime
    import pytz
    
    # Usar timezone de Ciudad de México
    mexico_tz = pytz.timezone('America/Mexico_City')
    fecha_actual = datetime.now(mexico_tz)
    
    if isinstance(usuario_id, str):
        usuario_id = ObjectId(usuario_id)
    
    # Convertir productos_data a formato correcto
    productos_procesados = []
    for producto in productos_data:
        producto_info = obtener_producto_por_id(producto['producto_id'])
        if producto_info:
            productos_procesados.append({
                'producto_id': ObjectId(producto['producto_id']),
                'nombre': producto_info['nombre'],
                'precio': producto_info['precio'],
                'cantidad': int(producto['cantidad']),
                'subtotal': producto_info['precio'] * int(producto['cantidad'])
            })
    
    pedido = {
        "usuario_id": usuario_id,
        "productos": productos_procesados,
        "total": total,
        "fecha": fecha_actual,
        "estado": estado
    }
    
    resultado = db.pedidos.insert_one(pedido)
    return resultado.inserted_id