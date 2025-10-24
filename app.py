# ecommerce-flask/app.py

from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from database import *
from bson import ObjectId
from werkzeug.security import check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui_super_segura'


# --- DECORADORES DE AUTENTICACIÓN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para ver esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') != 'admin':
            flash('No tienes permiso para acceder a esta página.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# --- RUTAS DE AUTENTICACIÓN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        usuario = obtener_usuario_por_correo(correo)

        if usuario and check_password_hash(usuario['password'], password):
            # Iniciar sesión guardando datos en la sesión
            session['user_id'] = usuario['id']
            session['user_nombre'] = usuario['nombre']
            session['rol'] = usuario['rol']
            flash(f'¡Bienvenido de nuevo, {usuario["nombre"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
            
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        password = request.form['password']

        # Verificar si el usuario ya existe
        if obtener_usuario_por_correo(correo):
            flash('El correo electrónico ya está registrado.', 'danger')
            return redirect(url_for('registro'))

        # Crear el nuevo usuario
        crear_usuario(nombre, correo, password)
        flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login'))

# ecommerce-flask/app.py
# ... (importaciones y otras rutas sin cambios)

@app.route('/productos/')
def listar_productos():
    """
    Muestra todos los productos o los filtra por categoría.
    El filtro usa el ObjectId de la categoría (pasado como ?categoria=<id>).
    """
    categoria_id = request.args.get('categoria')  # Se espera un ObjectId en la URL (por ejemplo /productos/?categoria=6523abc123...)

    if categoria_id:
        productos = obtener_productos_por_categoria(categoria_id)
        # Intentamos obtener el nombre de la categoría para mostrarlo en el título
        categoria = db.categorias.find_one({'_id': ObjectId(categoria_id)})
        titulo = categoria['nombre'] if categoria else "Productos filtrados"
    else:
        productos = obtener_productos()
        titulo = "Todos los Productos"

    return render_template('productos.html', productos=productos, titulo=titulo)

# ... (el resto de app.py sin cambios)

# --- RUTAS DE LA APLICACIÓN (Algunas ahora protegidas) ---
@app.route('/')
def index():
    categorias = obtener_categorias()
    return render_template('index.html', categorias=categorias)

# ... (Las rutas /productos y /producto/<id> no necesitan login)
#@app.route('/productos/')
#def listar_productos():
#    productos = obtener_productos()
#    return render_template('productos.html', productos=productos, titulo="Todos los Productos")

@app.route('/producto/<string:producto_id>')
def detalle_producto(producto_id):
    producto = obtener_producto_por_id(producto_id)
    if producto is None:
        abort(404)
    
    # Obtener reseñas del producto
    reseñas = obtener_reseñas_por_producto(producto_id)
    
    # Calcular promedio de calificaciones
    estadisticas_reseñas = calcular_promedio_calificacion(producto_id)
    
    # Verificar si el usuario puede escribir una reseña
    puede_reseñar = False
    ya_reseñó = False
    
    if 'user_id' in session:
        puede_reseñar = verificar_usuario_puede_reseñar(session['user_id'], producto_id)
        ya_reseñó = usuario_ya_reseño_producto(session['user_id'], producto_id)
    
    return render_template(
        'producto.html', 
        producto=producto, 
        reseñas=reseñas,
        estadisticas_reseñas=estadisticas_reseñas,
        puede_reseñar=puede_reseñar,
        ya_reseñó=ya_reseñó
    )

@app.route('/producto/<string:producto_id>/reseña', methods=['POST'])
@login_required
def crear_reseña_producto(producto_id):
    """Crea una nueva reseña para un producto."""
    try:
        calificacion = int(request.form.get('calificacion'))
        comentario = request.form.get('comentario', '').strip()
        
        # Validaciones
        if not (1 <= calificacion <= 5):
            flash('La calificación debe ser entre 1 y 5 estrellas.', 'danger')
            return redirect(url_for('detalle_producto', producto_id=producto_id))
        
        if len(comentario) < 10:
            flash('El comentario debe tener al menos 10 caracteres.', 'danger')
            return redirect(url_for('detalle_producto', producto_id=producto_id))
        
        # Verificar que el usuario puede reseñar este producto
        if not verificar_usuario_puede_reseñar(session['user_id'], producto_id):
            flash('Solo puedes reseñar productos que hayas comprado.', 'danger')
            return redirect(url_for('detalle_producto', producto_id=producto_id))
        
        # Verificar que no haya reseñado antes
        if usuario_ya_reseño_producto(session['user_id'], producto_id):
            flash('Ya has escrito una reseña para este producto.', 'warning')
            return redirect(url_for('detalle_producto', producto_id=producto_id))
        
        # Crear la reseña
        crear_reseña(producto_id, session['user_id'], calificacion, comentario)
        flash('¡Reseña agregada exitosamente!', 'success')
        
    except Exception as e:
        flash(f'Error al crear la reseña: {str(e)}', 'danger')
    
    return redirect(url_for('detalle_producto', producto_id=producto_id))

@app.route('/usuario/<string:usuario_id>')
@login_required  # RUTA PROTEGIDA
def perfil_usuario(usuario_id):
    """Muestra el perfil de un usuario"""
    # Validar que solo el usuario dueño o un admin acceda
    if session['rol'] != 'admin' and session['user_id'] != usuario_id:
        abort(403)
    
    usuario = obtener_usuario_por_id(usuario_id)
    if usuario is None:
        abort(404)
    
    return render_template('usuario.html', usuario=usuario)

@app.route('/carrito/')
@login_required
def ver_carrito():
    """Muestra el carrito actual del usuario autenticado"""
    try:
        usuario_id = ObjectId(session['user_id'])
    except Exception:
        flash('ID de usuario inválido en sesión.', 'danger')
        return render_template('carrito.html', items=[], total=0)

    usuario = obtener_usuario_por_id(usuario_id)
    if not usuario:
        flash('No se pudo encontrar la información del usuario.', 'danger')
        return render_template('carrito.html', items=[], total=0)

    carrito_data = obtener_carrito_por_usuario(usuario_id)
    return render_template(
        'carrito.html',
        items=carrito_data['items'],
        total=carrito_data['total']
    )

@app.route('/vaciar_carrito')
@login_required 
def vaciar_carrito():
    """Vacía el carrito del usuario autenticado"""
    try:
        usuario_id = ObjectId(session['user_id'])
    except Exception:
        flash('ID de usuario inválido en sesión.', 'danger')
        return redirect(url_for('ver_carrito'))

    usuario = obtener_usuario_por_id(usuario_id)
    if usuario:
        vaciar_carrito_db(usuario_id)
        flash('Carrito vaciado correctamente.', 'info')
    else:
        flash('No se pudo vaciar el carrito.', 'danger')

    return redirect(url_for('ver_carrito'))

@app.route('/agregar_al_carrito/<string:producto_id>', methods=['POST'])
@login_required
def agregar_al_carrito(producto_id):
    # Obtener la cantidad del formulario. Si no existe, usar 1 por defecto.
    try:
        cantidad = int(request.form.get('cantidad', 1))
    except (ValueError, TypeError):
        cantidad = 1
    
    usuario = obtener_usuario_por_id(session['user_id']) # Obtener el usuario para su ID numérico

    producto = obtener_producto_por_id(producto_id) # Obtener el producto para su ID numérico

    if usuario and producto:
        # Usar el ObjectId del usuario directamente desde session
        usuario_object_id = ObjectId(session['user_id'])
        producto_object_id = ObjectId(producto_id)
        
        # Bucle para agregar el producto la cantidad de veces especificada
        for _ in range(cantidad):
            agregar_producto_al_carrito_db(usuario_object_id, producto_object_id)
        
        flash(f'¡Se añadieron {cantidad} producto(s) al carrito!', 'success')
    else:
        flash('Error al añadir el producto.', 'danger')

    return redirect(request.referrer or url_for('listar_productos'))

@app.route('/actualizar_carrito/<string:producto_id>/<string:accion>', methods=['POST'])
@login_required
def actualizar_carrito(producto_id, accion):
    """Actualiza la cantidad de un producto en el carrito."""
    try:
        usuario_id = ObjectId(session['user_id'])
        
        if accion in ['incrementar', 'decrementar']:
            success = actualizar_cantidad_carrito(usuario_id, producto_id, accion)
            if success:
                if accion == 'incrementar':
                    flash('Cantidad actualizada en el carrito.', 'success')
                else:
                    flash('Cantidad actualizada en el carrito.', 'info')
            else:
                flash('Error al actualizar el carrito.', 'danger')
        else:
            flash('Acción no válida.', 'danger')
    except Exception as e:
        flash('Error al actualizar el carrito.', 'danger')
    
    return redirect(url_for('ver_carrito'))

@app.route('/eliminar_del_carrito/<string:producto_id>', methods=['POST'])
@login_required
def eliminar_del_carrito(producto_id):
    """Elimina completamente un producto del carrito."""
    try:
        usuario_id = ObjectId(session['user_id'])
        success = eliminar_producto_carrito(usuario_id, producto_id)
        if success:
            flash('Producto eliminado del carrito.', 'info')
        else:
            flash('Error al eliminar el producto del carrito.', 'danger')
    except Exception as e:
        flash('Error al eliminar el producto del carrito.', 'danger')
    
    return redirect(url_for('ver_carrito'))

@app.route('/proceder_pago', methods=['POST'])
@login_required
def proceder_pago():
    """Procesa el pago del carrito y crea un pedido."""
    try:
        usuario_id = ObjectId(session['user_id'])
    except Exception:
        flash('ID de usuario inválido en sesión.', 'danger')
        return redirect(url_for('ver_carrito'))

    # Obtener carrito actual
    carrito_data = obtener_carrito_por_usuario(usuario_id)
    
    if not carrito_data['items']:
        flash('Tu carrito está vacío.', 'warning')
        return redirect(url_for('ver_carrito'))

    # Verificar inventario suficiente para todos los productos
    productos_insuficientes = []
    for item in carrito_data['items']:
        # Obtener el producto para verificar inventario actual
        producto = obtener_producto_por_id(str(item.get('producto_id', '')))
        if not producto:
            productos_insuficientes.append(item['nombre'])
            continue
            
        if not verificar_inventario_suficiente(producto['_id'], item['cantidad']):
            productos_insuficientes.append(f"{item['nombre']} (disponible: {producto.get('inventario', 0)})")

    if productos_insuficientes:
        flash(f'Inventario insuficiente para: {", ".join(productos_insuficientes)}', 'danger')
        return redirect(url_for('ver_carrito'))

    # Reducir inventario de cada producto
    for item in carrito_data['items']:
        producto = obtener_producto_por_id(str(item.get('producto_id', '')))
        if producto:
            reducir_inventario_producto(producto['_id'], item['cantidad'])

    # Crear el pedido
    pedido_id = crear_pedido(usuario_id, carrito_data['items'], carrito_data['total'])
    
    # Vaciar el carrito
    vaciar_carrito_db(usuario_id)
    
    flash(f'¡Pedido realizado exitosamente! ID del pedido: {pedido_id}', 'success')
    return redirect(url_for('ver_pedidos'))

@app.route('/pedidos/')
@login_required
def ver_pedidos():
    """Muestra todos los pedidos del usuario autenticado."""
    try:
        usuario_id = ObjectId(session['user_id'])
    except Exception:
        flash('ID de usuario inválido en sesión.', 'danger')
        return render_template('pedidos.html', pedidos=[])

    pedidos = obtener_pedidos_por_usuario(usuario_id)
    return render_template('pedidos.html', pedidos=pedidos)

@app.route('/pedido/<string:pedido_id>')
@login_required
def detalle_pedido(pedido_id):
    """Muestra el detalle de un pedido específico."""
    pedido = obtener_pedido_por_id(pedido_id)
    
    if not pedido:
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('ver_pedidos'))
    
    # Verificar que el pedido pertenece al usuario actual (o es admin)
    if session.get('rol') != 'admin' and str(pedido['usuario_id']) != session['user_id']:
        flash('No tienes permiso para ver este pedido.', 'danger')
        return redirect(url_for('ver_pedidos'))
    
    return render_template('detalle_pedido.html', pedido=pedido)


# CRUD ADMINISTRADOR
# USUARIOS
@app.route('/usuarios/')
@login_required
@admin_required
def listar_usuarios():
    usuarios = obtener_usuarios()
    return render_template('index_usuario.html', usuarios=usuarios)  # index.html porque las plantillas están directas

@app.route('/usuarios/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_usuario_admin():
    if request.method == 'POST':
        nuevo_usuario = {
            "nombre": request.form["nombre"],
            "correo": request.form["correo"],
            "telefono": request.form["telefono"],
            "direccion": request.form["direccion"],
            "rol": request.form.get("rol", "cliente")
        }
        crear_usuario(nuevo_usuario["nombre"], nuevo_usuario["correo"], "123456")  # password por defecto
        flash('Usuario creado exitosamente.', 'success')
        return redirect(url_for('listar_usuarios'))
    return render_template('crear_usuario.html')

@app.route('/usuarios/editar/<string:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario_admin(id):
    usuario = obtener_usuario_por_id(id)
    if not usuario:
        return "Usuario no encontrado", 404
    if request.method == 'POST':
        db.usuarios.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "nombre": request.form["nombre"],
                "correo": request.form["correo"],
                "telefono": request.form.get("telefono"),
                "direccion": request.form.get("direccion"),
            }}
        )
        flash('Usuario actualizado.', 'success')
        return redirect(url_for('listar_usuarios'))
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/usuarios/eliminar/<string:id>')
@login_required
@admin_required
def eliminar_usuario_admin(id):
    db.usuarios.delete_one({"_id": ObjectId(id)})
    flash('Usuario eliminado.', 'info')
    return redirect(url_for('listar_usuarios'))

# CATEGORIAS
@app.route("/categorias/")
def listar_categorias():
    categorias = obtener_categorias()
    return render_template("index_categoria.html", categorias=categorias)

@app.route("/categorias/crear", methods=["GET", "POST"])
def crear_categoria_admin():
    if request.method == "POST":
        nueva_categoria = {
            "categoria_id": int(request.form["categoria_id"]),
            "nombre": request.form["nombre"],
            "descripcion": request.form["descripcion"],
            "activa": request.form.get("activa") == "1"
        }
        db.categorias.insert_one(nueva_categoria)
        return redirect(url_for("listar_categorias"))
    return render_template("crear_categoria.html")

@app.route("/categorias/editar/<string:id>", methods=["GET", "POST"])
def editar_categoria_admin(id):
    categoria = obtener_categoria_por_id(id)
    if not categoria:
        return "Categoría no encontrada", 404
    
    if request.method == "POST":
        db.categorias.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "nombre": request.form["nombre"],
                "descripcion": request.form["descripcion"],
                "activa": request.form.get("activa") == "1"
            }}
        )
        return redirect(url_for("listar_categorias"))
    return render_template("editar_categoria.html", categoria=categoria)

@app.route("/categorias/eliminar/<string:id>")
def eliminar_categoria_admin(id):
    db.categorias.delete_one({"_id": ObjectId(id)})
    flash('Categoría eliminada.', 'info')
    return redirect(url_for("listar_categorias"))

#PRODUCTOS
@app.route("/producto/")
def listar_producto_admin():
    productos = obtener_productos()
    return render_template("index_producto.html", productos=productos)

@app.route("/producto/crear", methods=["GET", "POST"])
def crear_producto_admin():
    if request.method == "POST":
        try:
            categoria_value = request.form.get("categoria", "").strip()
            if not categoria_value:
                flash('Debes seleccionar una categoría.', 'danger')
                categorias = obtener_categorias()
                return render_template("crear_producto.html", categorias=categorias)
            
            nuevo_producto = {
                "nombre": request.form["nombre"],
                "descripcion": request.form["descripcion"],
                "precio": float(request.form["precio"]),
                "categoria": ObjectId(categoria_value),
                "inventario": int(request.form["inventario"]),
                "activo": request.form.get("activo") == "1",
                "imagen_url": request.form.get("imagen_url", "")
            }
            db.productos.insert_one(nuevo_producto)
            flash('Producto creado exitosamente.', 'success')
            return redirect(url_for("listar_producto_admin"))
        except Exception as e:
            flash(f'Error al crear el producto: {str(e)}', 'danger')
            categorias = obtener_categorias()
            return render_template("crear_producto.html", categorias=categorias)
    
    categorias = obtener_categorias()
    return render_template("crear_producto.html", categorias=categorias)

@app.route("/producto/editar/<string:id>", methods=["GET", "POST"])
def editar_producto_admin(id):
    producto = obtener_producto_por_id(id)
    if not producto:
        return "Producto no encontrado", 404

    if request.method == "POST":
        try:
            categoria_value = request.form.get("categoria", "").strip()
            if not categoria_value:
                flash('Debes seleccionar una categoría.', 'danger')
                categorias = obtener_categorias()
                return render_template("editar_producto.html", producto=producto, categoria=categorias)
            
            db.productos.update_one(
                {"_id": ObjectId(id)},
                {"$set": {
                    "nombre": request.form["nombre"],
                    "descripcion": request.form["descripcion"],
                    "precio": float(request.form["precio"]),
                    "categoria": ObjectId(categoria_value),
                    "inventario": int(request.form["inventario"]),
                    "activo": request.form.get("activo") == "1",
                    "imagen_url": request.form.get("imagen_url", "")
                }}
            )
        except Exception as e:
            flash(f'Error al actualizar el producto: {str(e)}', 'danger')
            categorias = obtener_categorias()
            return render_template("editar_producto.html", producto=producto, categoria=categorias)
        flash('Producto actualizado.', 'success')
        return redirect(url_for("listar_producto_admin"))
    
    categorias = obtener_categorias()
    return render_template("editar_producto.html", producto=producto, categoria=categorias)

@app.route("/producto/eliminar/<string:id>")
def eliminar_producto_admin(id):
    db.productos.delete_one({"_id": ObjectId(id)})
    flash('Producto eliminado.', 'info')
    return redirect(url_for("listar_producto_admin"))

#PEDIDOS
@app.route("/pedido/")
@login_required
@admin_required
def listar_pedidos_admin():
    pedidos = obtener_pedidos_con_usuario()
    return render_template("index_pedido.html", pedidos=pedidos)

@app.route("/pedido/crear", methods=["GET", "POST"])
@login_required
@admin_required
def crear_pedido_admin():
    if request.method == "POST":
        try:
            usuario_id = request.form["usuario_id"]
            estado = request.form.get("estado", "pendiente")
            
            # Obtener productos seleccionados
            productos_data = []
            total = 0
            
            # Los productos vienen como listas paralelas
            productos_ids = request.form.getlist("producto_id")
            cantidades = request.form.getlist("cantidad")
            
            for i, producto_id in enumerate(productos_ids):
                if producto_id and i < len(cantidades):
                    cantidad = int(cantidades[i])
                    if cantidad > 0:
                        productos_data.append({
                            'producto_id': producto_id,
                            'cantidad': cantidad
                        })
                        
                        # Calcular total
                        producto_info = obtener_producto_por_id(producto_id)
                        if producto_info:
                            total += producto_info['precio'] * cantidad
            
            if productos_data:
                crear_pedido_desde_admin(usuario_id, productos_data, total, estado)
                flash('Pedido creado exitosamente.', 'success')
                return redirect(url_for("listar_pedidos_admin"))
            else:
                flash('Debe agregar al menos un producto al pedido.', 'danger')
                
        except Exception as e:
            flash(f'Error al crear el pedido: {str(e)}', 'danger')
    
    usuarios = obtener_usuarios()
    productos = obtener_productos()
    return render_template("crear_pedido.html", usuarios=usuarios, productos=productos)

@app.route("/pedido/ver/<string:id>", methods=["GET", "POST"])
@login_required
@admin_required
def ver_pedido_admin(id):
    pedido = obtener_pedido_por_id(id)
    if not pedido:
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('listar_pedidos_admin'))

    if request.method == "POST":
        try:
            estado = request.form.get("estado", pedido['estado'])
            
            # Actualizar estado
            db.pedidos.update_one(
                {"_id": ObjectId(id)},
                {"$set": {
                    "estado": estado
                }}
            )
            flash('Pedido actualizado exitosamente.', 'success')
            return redirect(url_for("listar_pedidos_admin"))
        except Exception as e:
            flash(f'Error al actualizar el pedido: {str(e)}', 'danger')
    
    return render_template("ver_pedido.html", pedido=pedido)

@app.route("/pedido/eliminar/<string:id>")
@login_required
@admin_required
def eliminar_pedido_admin(id):
    try:
        db.pedidos.delete_one({"_id": ObjectId(id)})
        flash('Pedido eliminado exitosamente.', 'info')
    except Exception as e:
        flash(f'Error al eliminar el pedido: {str(e)}', 'danger')
    
    return redirect(url_for("listar_pedidos_admin"))

# --- CRUD ADMINISTRADOR - RESEÑAS ---
@app.route('/admin/reseñas')
@login_required
@admin_required
def listar_reseñas_admin():
    """Lista todas las reseñas para el administrador."""
    reseñas = obtener_todas_las_reseñas_admin()
    return render_template('index_reseña.html', reseñas=reseñas)

@app.route('/admin/reseñas/<string:id>')
@login_required
@admin_required
def ver_reseña_admin(id):
    """Ver detalles de una reseña específica (solo lectura)."""
    reseña = obtener_reseña_por_id_admin(id)
    if not reseña:
        flash('Reseña no encontrada.', 'danger')
        return redirect(url_for('listar_reseñas_admin'))
    
    return render_template('ver_reseña.html', reseña=reseña)

@app.route('/admin/reseñas/eliminar/<string:id>')
@login_required
@admin_required
def eliminar_reseña_admin_route(id):
    """Elimina una reseña (solo para administradores)."""
    try:
        success = eliminar_reseña_admin(id)
        if success:
            flash('Reseña eliminada exitosamente.', 'info')
        else:
            flash('No se pudo eliminar la reseña.', 'danger')
    except Exception as e:
        flash(f'Error al eliminar la reseña: {str(e)}', 'danger')
    
    return redirect(url_for("listar_reseñas_admin"))

# --- CRUD ADMINISTRADOR - CARRITOS ---
@app.route('/admin/carritos')
@login_required
@admin_required
def listar_carritos_admin():
    """Lista todos los carritos para el administrador."""
    try:
        carritos = obtener_todos_los_carritos_admin()
        return render_template('index_carrito.html', carritos=carritos)
    except Exception as e:
        print(f"Error en listar_carritos_admin: {e}")
        flash('Error al cargar los carritos.', 'danger')
        return render_template('index_carrito.html', carritos=[])

@app.route('/admin/carritos/<string:usuario_id>')
@login_required
@admin_required
def ver_carrito_admin(usuario_id):
    """Ver detalles de un carrito específico."""
    try:
        carrito = obtener_carrito_detallado_admin(usuario_id)
        if not carrito:
            flash('Carrito no encontrado.', 'danger')
            return redirect(url_for('listar_carritos_admin'))
        
        return render_template('ver_carrito_admin.html', carrito=carrito)
        
    except Exception as e:
        print(f"Error en ver_carrito_admin: {e}")
        flash('Error al cargar el carrito.', 'danger')
        return redirect(url_for('listar_carritos_admin'))

@app.route('/admin/carritos/vaciar/<string:usuario_id>', methods=['POST'])
@login_required
@admin_required
def vaciar_carrito_admin_route(usuario_id):
    """Vacía un carrito específico (solo para administradores)."""
    try:
        success = vaciar_carrito_admin(usuario_id)
        if success:
            flash('Carrito vaciado exitosamente.', 'success')
        else:
            flash('No se pudo vaciar el carrito.', 'warning')
    except Exception as e:
        flash(f'Error al vaciar el carrito: {str(e)}', 'danger')
    
    return redirect(url_for("ver_carrito_admin", usuario_id=usuario_id))

@app.route('/admin/carritos/actualizar-producto/<string:usuario_id>/<string:producto_id>', methods=['POST'])
@login_required
@admin_required
def actualizar_producto_carrito_admin_route(usuario_id, producto_id):
    """Actualiza la cantidad de un producto en el carrito."""
    try:
        nueva_cantidad = int(request.form.get('cantidad', 1))
        
        if nueva_cantidad < 0:
            flash('La cantidad debe ser mayor o igual a 0.', 'warning')
        elif nueva_cantidad == 0:
            # Si la cantidad es 0, eliminar el producto
            success = eliminar_producto_carrito_admin(usuario_id, producto_id)
            if success:
                flash('Producto eliminado del carrito.', 'success')
            else:
                flash('No se pudo eliminar el producto.', 'warning')
        else:
            success = actualizar_cantidad_producto_carrito_admin(usuario_id, producto_id, nueva_cantidad)
            if success:
                flash(f'Cantidad actualizada a {nueva_cantidad}.', 'success')
            else:
                flash('No se pudo actualizar la cantidad.', 'warning')
                
    except ValueError:
        flash('Cantidad inválida.', 'danger')
    except Exception as e:
        flash(f'Error al actualizar el producto: {str(e)}', 'danger')
    
    return redirect(url_for("ver_carrito_admin", usuario_id=usuario_id))

@app.route('/admin/carritos/eliminar-producto/<string:usuario_id>/<string:producto_id>', methods=['POST'])
@login_required
@admin_required
def eliminar_producto_carrito_admin_route(usuario_id, producto_id):
    """Elimina un producto del carrito."""
    try:
        success = eliminar_producto_carrito_admin(usuario_id, producto_id)
        if success:
            flash('Producto eliminado del carrito.', 'success')
        else:
            flash('No se pudo eliminar el producto.', 'warning')
    except Exception as e:
        flash(f'Error al eliminar el producto: {str(e)}', 'danger')
    
    return redirect(url_for("ver_carrito_admin", usuario_id=usuario_id))

# -------------------------------
# DASHBOARD ADMIN (ejemplo)
# -------------------------------
""" @app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    usuarios = obtener_usuarios()
    return render_template('admin_dashboard.html', usuarios=usuarios) """


# (El resto de las rutas sin cambios)
if __name__ == '__main__':
    app.run(debug=True)