# ecommerce-flask/database.py

from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash
from datetime import datetime

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
                'imagen_url': 1,
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
                    'imagen_url': 1,
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
                    'imagen_url': 1,
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

def obtener_reseñas_por_producto(producto_id):
    """Obtiene todas las reseñas de un producto específico con información del usuario."""
    try:
        # Convertir producto_id a ObjectId si es necesario
        if isinstance(producto_id, str):
            producto_object_id = ObjectId(producto_id)
        else:
            producto_object_id = producto_id
        
        pipeline = [
            # Buscar reseñas por producto_id (solo ObjectId)
            {
                '$match': {
                    'producto_id': producto_object_id
                }
            },
            # Join con usuarios para obtener nombre del autor
            {
                '$lookup': {
                    'from': 'usuarios',
                    'localField': 'usuario_id',
                    'foreignField': '_id',
                    'as': 'usuario_info'
                }
            },
            # Descomponer usuario_info
            {
                '$unwind': {
                    'path': '$usuario_info',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # Proyectar campos necesarios
            {
                '$project': {
                    'producto_id': 1,
                    'calificacion': 1,
                    'comentario': 1,
                    'fecha': 1,
                    'usuario_nombre': '$usuario_info.nombre',
                    'usuario_id': 1
                }
            },
            # Ordenar por fecha más reciente
            {
                '$sort': {'fecha': -1}
            }
        ]
        
        reseñas_cursor = db.reseñas.aggregate(pipeline)
        return [_mapear_id(reseña) for reseña in reseñas_cursor]
        
    except Exception as e:
        print(f"Error en obtener_reseñas_por_producto: {e}")
        return []

def crear_reseña(producto_id, usuario_id, calificacion, comentario):
    """Crea una nueva reseña para un producto."""
    from datetime import datetime
    import pytz
    
    # Usar timezone de Ciudad de México
    mexico_tz = pytz.timezone('America/Mexico_City')
    fecha_actual = datetime.now(mexico_tz)
    
    # Convertir IDs a ObjectId si son strings
    if isinstance(producto_id, str):
        producto_object_id = ObjectId(producto_id)
    else:
        producto_object_id = producto_id
        
    if isinstance(usuario_id, str):
        usuario_object_id = ObjectId(usuario_id)
    else:
        usuario_object_id = usuario_id
    
    reseña = {
        "producto_id": producto_object_id,
        "usuario_id": usuario_object_id,
        "calificacion": int(calificacion),
        "comentario": comentario,
        "fecha": fecha_actual
    }
    
    resultado = db.reseñas.insert_one(reseña)
    return resultado.inserted_id

def verificar_usuario_puede_reseñar(usuario_id, producto_id):
    """Verifica si un usuario puede escribir una reseña para un producto (debe haberlo comprado)."""
    try:
        if isinstance(usuario_id, str):
            usuario_object_id = ObjectId(usuario_id)
        else:
            usuario_object_id = usuario_id
            
        if isinstance(producto_id, str):
            producto_object_id = ObjectId(producto_id)
        else:
            producto_object_id = producto_id
        
        # Buscar si el usuario ha comprado este producto
        pedido_con_producto = db.pedidos.find_one({
            'usuario_id': usuario_object_id,
            'productos.producto_id': producto_object_id,
            'estado': {'$in': ['enviado', 'entregado']}  # Solo pedidos enviados o entregados
        })
        
        return pedido_con_producto is not None
        
    except Exception:
        return False

def usuario_ya_reseño_producto(usuario_id, producto_id):
    """Verifica si un usuario ya escribió una reseña para este producto."""
    try:
        if isinstance(usuario_id, str):
            usuario_object_id = ObjectId(usuario_id)
        else:
            usuario_object_id = usuario_id
            
        if isinstance(producto_id, str):
            producto_object_id = ObjectId(producto_id)
        else:
            producto_object_id = producto_id
        
        reseña_existente = db.reseñas.find_one({
            'usuario_id': usuario_object_id,
            '$or': [
                {'producto_id': producto_object_id},
                {'producto_id': producto_id}
            ]
        })
        
        return reseña_existente is not None
        
    except Exception:
        return False

# --- Funciones Admin de Reseñas ---
def obtener_todas_las_reseñas_admin():
    """Obtiene todas las reseñas con información de usuario y producto para el admin."""
    try:
        pipeline = [
            # Join con usuarios para obtener nombre del autor
            {
                '$lookup': {
                    'from': 'usuarios',
                    'localField': 'usuario_id',
                    'foreignField': '_id',
                    'as': 'usuario_info'
                }
            },
            # Join con productos para obtener nombre del producto
            {
                '$lookup': {
                    'from': 'productos',
                    'localField': 'producto_id',
                    'foreignField': '_id',
                    'as': 'producto_info'
                }
            },
            # Descomponer usuario_info
            {
                '$unwind': {
                    'path': '$usuario_info',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # Descomponer producto_info
            {
                '$unwind': {
                    'path': '$producto_info',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # Proyectar campos necesarios
            {
                '$project': {
                    'producto_id': 1,
                    'usuario_id': 1,
                    'calificacion': 1,
                    'comentario': 1,
                    'fecha': 1,
                    'usuario_nombre': '$usuario_info.nombre',
                    'usuario_correo': '$usuario_info.correo',
                    'producto_nombre': '$producto_info.nombre',
                    'producto_precio': '$producto_info.precio'
                }
            },
            # Ordenar por fecha más reciente
            {
                '$sort': {'fecha': -1}
            }
        ]
        
        reseñas_cursor = db.reseñas.aggregate(pipeline)
        return [_mapear_id(reseña) for reseña in reseñas_cursor]
        
    except Exception as e:
        print(f"Error en obtener_todas_las_reseñas_admin: {e}")
        return []

def obtener_reseña_por_id_admin(reseña_id):
    """Obtiene una reseña específica con información completa para el admin."""
    try:
        if isinstance(reseña_id, str):
            reseña_object_id = ObjectId(reseña_id)
        else:
            reseña_object_id = reseña_id
        
        pipeline = [
            # Buscar reseña específica
            {
                '$match': {'_id': reseña_object_id}
            },
            # Join con usuarios
            {
                '$lookup': {
                    'from': 'usuarios',
                    'localField': 'usuario_id',
                    'foreignField': '_id',
                    'as': 'usuario_info'
                }
            },
            # Join con productos
            {
                '$lookup': {
                    'from': 'productos',
                    'localField': 'producto_id',
                    'foreignField': '_id',
                    'as': 'producto_info'
                }
            },
            # Descomponer arrays
            {
                '$unwind': {
                    'path': '$usuario_info',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$unwind': {
                    'path': '$producto_info',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # Proyectar todos los campos
            {
                '$project': {
                    'producto_id': 1,
                    'usuario_id': 1,
                    'calificacion': 1,
                    'comentario': 1,
                    'fecha': 1,
                    'usuario_nombre': '$usuario_info.nombre',
                    'usuario_correo': '$usuario_info.correo',
                    'usuario_telefono': '$usuario_info.telefono',
                    'producto_nombre': '$producto_info.nombre',
                    'producto_precio': '$producto_info.precio',
                    'producto_descripcion': '$producto_info.descripcion'
                }
            }
        ]
        
        resultado = list(db.reseñas.aggregate(pipeline))
        if resultado:
            return _mapear_id(resultado[0])
        return None
        
    except Exception as e:
        print(f"Error en obtener_reseña_por_id_admin: {e}")
        return None

def eliminar_reseña_admin(reseña_id):
    """Elimina una reseña (solo para administradores)."""
    try:
        if isinstance(reseña_id, str):
            reseña_object_id = ObjectId(reseña_id)
        else:
            reseña_object_id = reseña_id
        
        resultado = db.reseñas.delete_one({'_id': reseña_object_id})
        return resultado.deleted_count > 0
        
    except Exception as e:
        print(f"Error en eliminar_reseña_admin: {e}")
        return False

def calcular_promedio_calificacion(producto_id):
    """Calcula el promedio de calificaciones de un producto."""
    try:
        if isinstance(producto_id, str):
            producto_object_id = ObjectId(producto_id)
        else:
            producto_object_id = producto_id
        
        pipeline = [
            {
                '$match': {
                    'producto_id': producto_object_id
                }
            },
            {
                '$group': {
                    '_id': None,
                    'promedio': {'$avg': '$calificacion'},
                    'total_reseñas': {'$sum': 1}
                }
            }
        ]
        
        resultado = list(db.reseñas.aggregate(pipeline))
        if resultado:
            return {
                'promedio': round(resultado[0]['promedio'], 1),
                'total': resultado[0]['total_reseñas']
            }
        else:
            return {'promedio': 0, 'total': 0}
            
    except Exception:
        return {'promedio': 0, 'total': 0}

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
        # Preservar productos incluso si el lookup no encuentra coincidencias
        {'$unwind': {
            'path': '$producto_info',
            'preserveNullAndEmptyArrays': True
        }},
        # Filtrar solo productos que existen
        {'$match': {'producto_info': {'$ne': None}}},
        {
            '$group': {
                '_id': '$producto_info._id',
                'nombre': {'$first': '$producto_info.nombre'},
                'precio': {'$first': '$producto_info.precio'},
                'imagen_url': {'$first': '$producto_info.imagen_url'},
                'cantidad': {'$sum': 1},
                'subtotal': {'$sum': '$producto_info.precio'}
            }
        },
        {
            '$project': {
                'producto_id': '$_id',
                'nombre': 1,
                'precio': 1,
                'imagen_url': 1,
                'cantidad': 1,
                'subtotal': 1
            }
        }
    ]

    items = list(db.carrito.aggregate(pipeline))
    total = sum(item.get('subtotal', 0) for item in items)

    # Limpiar productos fantasmas (productos que ya no existen en la BD)
    if carrito.get('productos'):
        productos_validos = [item['producto_id'] for item in items]
        productos_actuales = carrito.get('productos', [])
        
        # Contar cuántos productos fantasmas hay
        productos_fantasmas = [p for p in productos_actuales if p not in productos_validos]
        
        if productos_fantasmas:
            print(f"Limpiando {len(productos_fantasmas)} productos fantasmas del carrito del usuario {usuario_id}")
            # Mantener solo los productos válidos
            productos_limpios = []
            for item in items:
                productos_limpios.extend([item['producto_id']] * item['cantidad'])
            
            db.carrito.update_one(
                {'usuario_id': usuario_id},
                {'$set': {
                    'productos': productos_limpios,
                    'total': total
                }}
            )
        else:
            # Solo actualizar el total si no hay productos fantasmas
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

def actualizar_cantidad_carrito(usuario_id, producto_id, accion):
    """Actualiza la cantidad de un producto en el carrito (incrementar o decrementar)."""
    if isinstance(usuario_id, str):
        usuario_id = ObjectId(usuario_id)
    if isinstance(producto_id, str):
        producto_id = ObjectId(producto_id)
    
    carrito = db.carrito.find_one({'usuario_id': usuario_id})
    if not carrito:
        return False
    
    productos = carrito.get('productos', [])
    
    if accion == 'incrementar':
        # Agregar una instancia más del producto
        db.carrito.update_one(
            {'usuario_id': usuario_id},
            {'$push': {'productos': producto_id}}
        )
    elif accion == 'decrementar':
        # Contar cuántas veces aparece el producto
        count = productos.count(producto_id)
        if count > 1:
            # Si hay más de 1, eliminar solo una instancia
            db.carrito.update_one(
                {'usuario_id': usuario_id},
                {'$pull': {'productos': producto_id}},
                {'multi': False}  # Solo eliminar una instancia
            )
        elif count == 1:
            # Si solo hay 1, eliminar completamente
            db.carrito.update_one(
                {'usuario_id': usuario_id},
                {'$pull': {'productos': producto_id}}
            )
    
    return True

def eliminar_producto_carrito(usuario_id, producto_id):
    """Elimina completamente un producto del carrito (todas las instancias)."""
    if isinstance(usuario_id, str):
        usuario_id = ObjectId(usuario_id)
    if isinstance(producto_id, str):
        producto_id = ObjectId(producto_id)
    
    db.carrito.update_one(
        {'usuario_id': usuario_id},
        {'$pull': {'productos': producto_id}}
    )
    return True

# --- Funciones Admin de Carritos ---
def obtener_todos_los_carritos_admin():
    """Obtiene todos los carritos con información de usuario y productos para el admin."""
    try:
        pipeline = [
            # Join con usuarios para obtener información del usuario
            {
                '$lookup': {
                    'from': 'usuarios',
                    'localField': 'usuario_id',
                    'foreignField': '_id',
                    'as': 'usuario_info'
                }
            },
            # Descomponer usuario_info
            {
                '$unwind': {
                    'path': '$usuario_info',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # Calcular estadísticas del carrito
            {
                '$addFields': {
                    'productos_unicos': {
                        '$size': {
                            '$setUnion': [
                                {'$ifNull': ['$productos', []]},
                                []
                            ]
                        }
                    },
                    'cantidad_total': {
                        '$size': {'$ifNull': ['$productos', []]}
                    },
                    'fecha_modificacion': {
                        '$ifNull': ['$fecha_modificacion', '$$NOW']
                    }
                }
            },
            # Proyectar campos necesarios
            {
                '$project': {
                    'usuario_id': 1,
                    'productos': 1,
                    'total': {'$ifNull': ['$total', 0]},
                    'fecha_modificacion': 1,
                    'productos_unicos': 1,
                    'cantidad_total': 1,
                    'usuario_nombre': '$usuario_info.nombre',
                    'usuario_correo': '$usuario_info.correo',
                    'usuario_telefono': '$usuario_info.telefono',
                    'tiene_productos': {
                        '$gt': ['$cantidad_total', 0]
                    }
                }
            },
            # Ordenar por fecha de modificación más reciente
            {
                '$sort': {'fecha_modificacion': -1}
            }
        ]
        
        carritos_cursor = db.carrito.aggregate(pipeline)
        carritos = [_mapear_id(carrito) for carrito in carritos_cursor]
        
        return carritos
        
    except Exception as e:
        print(f"Error en obtener_todos_los_carritos_admin: {e}")
        import traceback
        traceback.print_exc()
        return []

def obtener_carrito_detallado_admin(usuario_id):
    """Obtiene un carrito específico con detalles de productos para el admin."""
    try:
        if isinstance(usuario_id, str):
            usuario_object_id = ObjectId(usuario_id)
        else:
            usuario_object_id = usuario_id
        
        # Usar la función existente para obtener productos del carrito
        carrito_data = obtener_carrito_por_usuario(usuario_object_id)
        
        # Obtener información del usuario
        usuario = db.usuarios.find_one({'_id': usuario_object_id})
        if not usuario:
            return None
            
        # Crear el objeto de respuesta con la estructura que espera el template
        resultado = {
            'usuario_id': str(usuario_object_id),
            'productos': carrito_data.get('items', []),
            'total': carrito_data.get('total', 0),
            'usuario': {
                'id': str(usuario['_id']),
                'nombre': usuario.get('nombre', 'Usuario Desconocido'),
                'correo': usuario.get('correo', 'Email no disponible'),
                'telefono': usuario.get('telefono', 'No disponible'),
                'direccion': usuario.get('direccion', 'No disponible')
            }
        }
        
        return resultado
        
    except Exception as e:
        print(f"Error en obtener_carrito_detallado_admin: {e}")
        import traceback
        traceback.print_exc()
        return None

def vaciar_carrito_admin(usuario_id):
    """Vacía un carrito específico (solo para administradores)."""
    try:
        if isinstance(usuario_id, str):
            usuario_object_id = ObjectId(usuario_id)
        else:
            usuario_object_id = usuario_id
        
        resultado = db.carrito.update_one(
            {'usuario_id': usuario_object_id},
            {'$set': {
                'productos': [],
                'total': 0,
                'fecha_modificacion': datetime.now()
            }}
        )
        return resultado.modified_count > 0
        
    except Exception as e:
        print(f"Error en vaciar_carrito_admin: {e}")
        return False

def actualizar_cantidad_producto_carrito_admin(usuario_id, producto_id, nueva_cantidad):
    """Actualiza la cantidad de un producto en el carrito (admin)."""
    try:
        if isinstance(usuario_id, str):
            usuario_object_id = ObjectId(usuario_id)
        else:
            usuario_object_id = usuario_id
            
        if isinstance(producto_id, str):
            producto_object_id = ObjectId(producto_id)
        else:
            producto_object_id = producto_id
        
        # Obtener el carrito actual
        carrito = db.carrito.find_one({'usuario_id': usuario_object_id})
        if not carrito:
            return False
        
        # Obtener productos actuales
        productos = carrito.get('productos', [])
        
        # Filtrar el producto a modificar
        productos_filtrados = [p for p in productos if p != producto_object_id]
        
        # Agregar la nueva cantidad
        nuevos_productos = productos_filtrados + [producto_object_id] * int(nueva_cantidad)
        
        # Actualizar el carrito
        db.carrito.update_one(
            {'usuario_id': usuario_object_id},
            {'$set': {
                'productos': nuevos_productos,
                'fecha_modificacion': datetime.now()
            }}
        )
        
        # Recalcular el total
        obtener_carrito_por_usuario(usuario_object_id)
        
        return True
        
    except Exception as e:
        print(f"Error en actualizar_cantidad_producto_carrito_admin: {e}")
        import traceback
        traceback.print_exc()
        return False

def eliminar_producto_carrito_admin(usuario_id, producto_id):
    """Elimina todas las unidades de un producto del carrito (admin)."""
    try:
        if isinstance(usuario_id, str):
            usuario_object_id = ObjectId(usuario_id)
        else:
            usuario_object_id = usuario_id
            
        if isinstance(producto_id, str):
            producto_object_id = ObjectId(producto_id)
        else:
            producto_object_id = producto_id
        
        # Eliminar todas las instancias del producto
        resultado = db.carrito.update_one(
            {'usuario_id': usuario_object_id},
            {
                '$pull': {'productos': producto_object_id},
                '$set': {'fecha_modificacion': datetime.now()}
            }
        )
        
        # Recalcular el total
        obtener_carrito_por_usuario(usuario_object_id)
        
        return resultado.modified_count > 0
        
    except Exception as e:
        print(f"Error en eliminar_producto_carrito_admin: {e}")
        return False

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
                'subtotal': producto_info['precio'] * int(producto['cantidad']),
                'imagen_url': producto_info.get('imagen_url', '')
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