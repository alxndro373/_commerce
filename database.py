# ecommerce-flask/database.py

from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash

# --- Configuración de la Conexión a MongoDB ---
client = MongoClient('mongodb://localhost:27017/')
db = client['e_commerce_pc']


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
    categorias_cursor = db.categorias.find()
    return [_mapear_id(cat) for cat in categorias_cursor]

def obtener_productos_por_categoria(nombre_categoria):
    """
    Obtiene productos de una categoría específica usando el pipeline de agregación.
    """
    pipeline = [
        {
            '$lookup': {
                'from': "categorias",
                'localField': "categoria_id",
                'foreignField': "categoria_id",
                'as': "categoria_info"
            }
        },
        {
            '$unwind': "$categoria_info"
        },
        {
            '$match': {
                "categoria_info.nombre": nombre_categoria
            }
        },
        {
            '$project': {
                # Mantenemos los campos originales que necesita la plantilla
                'nombre': 1,
                'descripcion': 1,
                'precio': 1,
                'categoria_id': 1,
                # Puedes añadir más campos si los necesitas
            }
        }
    ]
    productos_cursor = db.productos.aggregate(pipeline)
    return [_mapear_id(p) for p in productos_cursor]

def obtener_productos():
    productos_cursor = db.productos.find()
    return [_mapear_id(prod) for prod in productos_cursor]

def obtener_producto_por_id(documento):
    try:
        producto = db.productos.find_one({'_id': ObjectId(documento)})
        return _mapear_id(producto)
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
def obtener_carrito_por_usuario(usuario_id_numerico):
    """
    Obtiene los productos en el carrito de un usuario y calcula el total
    usando un pipeline de agregación.
    """
    pipeline = [
        # 1. Encontrar el carrito del usuario
        {'$match': {'usuario_id': usuario_id_numerico}},
        # 2. Desenrollar el array de productos para procesar cada ID individualmente
        {'$unwind': '$producto_id'},
        # 3. Contar cuántas veces aparece cada producto (cantidad)
        {'$group': {'_id': '$producto_id', 'cantidad': {'$sum': 1}}},
        # 4. Unir con la colección de productos para obtener los detalles
        {
            '$lookup': {
                'from': 'productos',
                'localField': '_id',
                'foreignField': 'producto_id',
                'as': 'producto_info'
            }
        },
        # 5. Desenrollar el resultado del lookup
        {'$unwind': '$producto_info'},
        # 6. Darle forma al documento final, calculando el subtotal
        {
            '$project': {
                '_id': 0,
                'id': '$producto_info._id',
                'nombre': '$producto_info.nombre',
                'precio': '$producto_info.precio',
                'cantidad': '$cantidad',
                'subtotal': {'$multiply': ['$cantidad', '$producto_info.precio']}
            }
        }
    ]
    
    items_cursor = db.carrito.aggregate(pipeline)
    items = [_mapear_id(item) for item in items_cursor]
    
    # Calcular el total sumando los subtotales
    total = sum(item['subtotal'] for item in items)
    db.carrito.update_one(
        {'usuario_id': usuario_id_numerico},
        {'$set': {'total': total}},
        upsert=True)
    return {'items': items, 'total': total}


def agregar_producto_al_carrito_db(usuario_id_numerico, producto_id_numerico):
    """Agrega un producto al carrito de un usuario en la BD."""
    db.carrito.update_one(
        {'usuario_id': usuario_id_numerico},
        {'$push': {'producto_id': producto_id_numerico},},
        
        upsert=True  # Crea el carrito si no existe
    )

def vaciar_carrito_db(usuario_id_numerico):
    """Vacía el carrito de un usuario en la BD (establece el array de productos a vacío)."""
    db.carrito.update_one(
        {'usuario_id': usuario_id_numerico},
        {'$set': {'producto_id': [], 'total': 0}}    
    )