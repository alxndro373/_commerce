# ecommerce-flask/database.py

from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash

# --- Configuración de la Conexión a MongoDB ---
client = MongoClient('mongodb://localhost:27017/')
db = client['e_commerce_pc']

# --- IMPORTANTE: SCRIPT ÚNICO PARA ACTUALIZAR USUARIOS ---
def inicializar_usuarios_con_roles_y_passwords():
    """
    Este script se ejecuta UNA SOLA VEZ para añadir passwords y roles
    a los usuarios existentes en la base de datos.
    """
    usuarios = db.usuarios.find()
    admin_emails = ["kevin@example.com", "alex@example.com"] # Lista de administradores

    for usuario in usuarios:
        # Revisa si el usuario ya tiene una contraseña para no sobrescribirla.
        if 'password' not in usuario:
            rol = 'admin' if usuario['correo'] in admin_emails else 'cliente'
            
            # 🔐 AQUÍ OCURRE LA MAGIA DEL HASHEO
            # Se genera el hash para la contraseña "password123"
            password_hasheada = generate_password_hash("password123")
            
            db.usuarios.update_one(
                {'_id': usuario['_id']},
                {'$set': {'password': password_hasheada, 'rol': rol}}
            )
    print("Usuarios actualizados con roles y contraseñas hasheadas.")

# ... (el resto de las funciones sin cambios) ...

def _mapear_id(documento):
    if documento and '_id' in documento:
        documento['id'] = str(documento['_id'])
    return documento

# --- IMPORTANTE: SCRIPT ÚNICO PARA ACTUALIZAR USUARIOS ---
#def inicializar_usuarios_con_roles_y_passwords():
    """
    Este script se ejecuta UNA SOLA VEZ para añadir passwords y roles
    a los usuarios existentes en la base de datos.
    """
    usuarios = db.usuarios.find()
    admin_email = "kevin@example.com" # Definimos un admin

    for usuario in usuarios:
        # Si el usuario no tiene un rol, se lo asignamos
        if 'rol' not in usuario:
            rol = 'admin' if usuario['correo'] == admin_email else 'cliente'
            # Hasheamos una contraseña por defecto "password123"
            password_hasheada = generate_password_hash("password123")
            
            db.usuarios.update_one(
                {'_id': usuario['_id']},
                {'$set': {'password': password_hasheada, 'rol': rol}}
            )
    print("Usuarios actualizados con roles y contraseñas hasheadas.")

# Llama a esta función una vez desde tu terminal para preparar la DB:
# python -c 'from database import inicializar_usuarios_con_roles_y_passwords; inicializar_usuarios_con_roles_y_passwords()'


def obtener_usuario_por_correo(correo):
    """Busca un usuario por su correo electrónico."""
    usuario = db.usuarios.find_one({'correo': correo})
    return _mapear_id(usuario)

# --- Las demás funciones permanecen igual ---
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

def obtener_producto_por_id(producto_id):
    try:
        producto = db.productos.find_one({'_id': ObjectId(producto_id)})
        return _mapear_id(producto)
    except Exception:
        return None

def obtener_reseñas():
    reseñas_cursor = db.reseñas.find()
    return [_mapear_id(res) for res in reseñas_cursor]

def obtener_usuarios():
    usuarios_cursor = db.usuarios.find()
    return [_mapear_id(user) for user in usuarios_cursor]
    
def obtener_usuario_por_id(usuario_id):
    try:
        usuario = db.usuarios.find_one({'_id': ObjectId(usuario_id)})
        return _mapear_id(usuario)
    except Exception:
        return None