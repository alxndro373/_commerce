# ecommerce-flask/app.py

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
    """Muestra todos los productos o los filtra por categoría usando agregación."""
    
    # Ahora buscamos por nombre de categoría en la URL
    categoria_nombre = request.args.get('categoria') 

    if categoria_nombre:
        # Si se especifica una categoría, usamos la nueva función eficiente
        productos = obtener_productos_por_categoria(categoria_nombre)
        titulo = categoria_nombre
    else:
        # Si no, mostramos todos los productos
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
    # ... Lógica de reseñas ...
    return render_template('producto.html', producto=producto, reseñas=[])


@app.route('/usuario/<string:usuario_id>')
@login_required # <-- RUTA PROTEGIDA
def perfil_usuario(usuario_id):
    # Opcional: verificar que el usuario solo vea su propio perfil si no es admin
    if session['rol'] != 'admin' and session['user_id'] != usuario_id:
        abort(403) # Error de "prohibido"
    
    usuario = obtener_usuario_por_id(usuario_id)
    if usuario is None:
        abort(404)
    return render_template('usuario.html', usuario=usuario)

@app.route('/carrito/')
@login_required 
def ver_carrito():
    # Obtener el usuario para conseguir su ID numérico
    usuario = obtener_usuario_por_id(session['user_id'])
    if not usuario or 'usuario_id' not in usuario:
        flash('No se pudo encontrar la información del usuario.', 'danger')
        return render_template('carrito.html', items=[], total=0)
    
    usuario_id_numerico = usuario['usuario_id']
    
    # Obtener el carrito desde la base de datos
    carrito_data = obtener_carrito_por_usuario(usuario_id_numerico)
    
    return render_template('carrito.html', items=carrito_data['items'], total=carrito_data['total'])

@app.route('/vaciar_carrito')
@login_required 
def vaciar_carrito():
    usuario = obtener_usuario_por_id(session['user_id'])
    if usuario and 'usuario_id' in usuario:
        vaciar_carrito_db(usuario['usuario_id'])
        flash('Carrito vaciado.', 'info')
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

    if usuario and producto and 'usuario_id' in usuario and 'producto_id' in producto:
        usuario_id_numerico = usuario['usuario_id']
        producto_id_numerico = producto['producto_id']
        
        # Bucle para agregar el producto la cantidad de veces especificada
        for _ in range(cantidad):
            agregar_producto_al_carrito_db(usuario_id_numerico, producto_id_numerico)
        
        flash(f'¡Se añadieron {cantidad} producto(s) al carrito!', 'success')
    else:
        flash('Error al añadir el producto.', 'danger')

    return redirect(request.referrer or url_for('listar_productos'))


# RUTA DE EJEMPLO PARA ADMINISTRADOR
@app.route('/admin/dashboard')
@login_required
@admin_required # RUTA PROTEGIDA POR ROL DE ADMIN
def admin_dashboard():
    # Lógica para que el admin gestione productos, usuarios, y todo lo demas.

    usuarios = obtener_usuarios()
    return render_template('admin_dashboard.html', usuarios=usuarios)


# (El resto de las rutas sin cambios)
if __name__ == '__main__':
    app.run(debug=True)