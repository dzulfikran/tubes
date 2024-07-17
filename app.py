from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from models import db, User, Karyawan, Product, TransaksiPenjualan, DetailTransaksiPenjualan, TransaksiPembelian, DetailTransaksiPembelian
from config import Config
from sqlalchemy import func
import calendar
import json

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Create the database and tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('login_pemilik.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Clear any existing session keys to avoid conflicts
        session.pop('user_id', None)
        session.pop('karyawan_id', None)
        session.pop('owner_id', None)
        session.pop('role', None)
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = 'pemilik'
            flash('Login berhasil!', 'success')
            return redirect(url_for('beranda'))
        else:
            flash('Login gagal. Periksa username dan password.', 'danger')
    
    return render_template('login_pemilik.html')

@app.route('/login/karyawan', methods=['GET', 'POST'])
def login_karyawan():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Clear any existing session keys to avoid conflicts
        session.pop('user_id', None)
        session.pop('karyawan_id', None)
        session.pop('owner_id', None)
        session.pop('role', None)

        karyawan = Karyawan.query.filter_by(username=username).first()
        
        if karyawan and check_password_hash(karyawan.password, password):
            session['user_id'] = karyawan.id
            session['karyawan_id'] = karyawan.id
            session['owner_id'] = karyawan.owner_id
            session['role'] = 'karyawan'
            flash('Login berhasil!', 'success')
            return redirect(url_for('beranda'))
        else:
            flash('Login gagal. Periksa username dan password.', 'danger')
    
    return render_template('login_karyawan.html')
  
@app.route('/daftar', methods=['GET', 'POST'])
def daftar():
    if request.method == 'POST':
        nama_toko = request.form['nama_toko']
        nama_pemilik = request.form['nama_pemilik']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        email = request.form['email']
        phone = request.form['phone']
        profile_pic = request.files['profile_pic']
        image_filename = secure_filename(profile_pic.filename)
        profile_pic.save(os.path.join(app.config['FOLDER_PROFILE_P'], image_filename))

        new_user = User(
            nama_toko=nama_toko,
            nama_pemilik=nama_pemilik,
            username=username,
            password=password,
            email=email,
            phone=phone,
            profile_pic=image_filename,
            role='pemilik'
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('daftar.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/beranda")
def beranda():
    if 'user_id' in session:
        user_id = session.get('user_id')
        role = session.get('role')
        user = User.query.get(user_id)
        if role == 'pemilik':
            nama_toko = user.nama_toko
        else:
            karyawan = Karyawan.query.filter_by(id=user.id).first()
            if karyawan:
                nama_toko = karyawan.owner.nama_toko
            else:
                nama_toko = 'Toko Tidak Diketahui'

    # Pemasukan dan pengeluaran
    today = datetime.today().date()
    start_of_month = today.replace(day=1)
    
    if 'user_id' in session:
        user_id = session.get('user_id')
        role = session.get('role')
        user = User.query.get(user_id)
        if role == 'pemilik':
            user_filter = TransaksiPenjualan.user_id == user.id
            user_filter_pembelian = TransaksiPembelian.user_id == user.id
        else:
            karyawan = Karyawan.query.filter_by(id=user.id).first()
            user_filter = TransaksiPenjualan.user_id == karyawan.owner_id
            user_filter_pembelian =  TransaksiPembelian.user_id == karyawan.owner_id 
    
        # Pemasukan
        daily_sales = db.session.query(func.sum(TransaksiPenjualan.total_harga)) \
                                .filter(TransaksiPenjualan.tanggal == today, user_filter).scalar() or 0
        monthly_sales = db.session.query(func.sum(TransaksiPenjualan.total_harga)) \
                                .filter(TransaksiPenjualan.tanggal >= start_of_month, user_filter).scalar() or 0

        yesterday = today - timedelta(days=1)
        previous_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        
        daily_sales_yesterday = db.session.query(func.sum(TransaksiPenjualan.total_harga)) \
                                        .filter(TransaksiPenjualan.tanggal == yesterday, user_filter).scalar() or 0
        monthly_sales_last_month = db.session.query(func.sum(TransaksiPenjualan.total_harga)) \
                                            .filter(TransaksiPenjualan.tanggal >= previous_month_start,
                                                    TransaksiPenjualan.tanggal < start_of_month, 
                                                    user_filter).scalar() or 0

        if daily_sales_yesterday != 0:
            daily_increase = ((daily_sales - daily_sales_yesterday) / daily_sales_yesterday * 100)
        else:
            daily_increase = 0

        daily_increase = f"{daily_increase:.2f}%"

        if daily_sales > daily_sales_yesterday:
            daily_increase = f"+{daily_increase}"
        elif daily_sales < daily_sales_yesterday:
            daily_increase = f"{daily_increase}"

        if monthly_sales_last_month != 0:
            monthly_increase = ((monthly_sales - monthly_sales_last_month) / monthly_sales_last_month * 100)
        else:
            monthly_increase = 0

        monthly_increase = f"{monthly_increase:.2f}%"

        if monthly_sales > monthly_sales_last_month:
            monthly_increase = f"+{monthly_increase}"
        elif monthly_sales < monthly_sales_last_month:
            monthly_increase = f"{monthly_increase}"

        # Pengeluaran
        daily_purchases = db.session.query(func.sum(TransaksiPembelian.total_harga)) \
                                .filter(TransaksiPembelian.tanggal == today, user_filter_pembelian).scalar() or 0
        monthly_purchases = db.session.query(func.sum(TransaksiPembelian.total_harga)) \
                                .filter(TransaksiPembelian.tanggal >= start_of_month, user_filter_pembelian).scalar() or 0

        yesterday = today - timedelta(days=1)
        previous_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        
        daily_purchases_yesterday = db.session.query(func.sum(TransaksiPembelian.total_harga)) \
                                        .filter(TransaksiPembelian.tanggal == yesterday, user_filter_pembelian).scalar() or 0
        monthly_purchases_last_month = db.session.query(func.sum(TransaksiPembelian.total_harga)) \
                                            .filter(TransaksiPembelian.tanggal >= previous_month_start,
                                                    TransaksiPembelian.tanggal < start_of_month, 
                                                    user_filter).scalar() or 0

        if daily_purchases_yesterday != 0:
            daily_purchases_increase = ((daily_purchases - daily_purchases_yesterday) / daily_purchases_yesterday * 100)
        else:
            daily_purchases_increase = 0

        daily_purchases_increase = f"{daily_purchases_increase:.2f}%"

        if daily_purchases > daily_purchases_yesterday:
            daily_purchases_increase = f"+{daily_purchases_increase}"
        elif daily_purchases < daily_purchases_yesterday:
            daily_purchases_increase = f"{daily_purchases_increase}"

        if monthly_purchases_last_month != 0:
            monthly_purchases_increase = ((monthly_purchases - monthly_purchases_last_month) / monthly_purchases_last_month * 100)
        else:
            monthly_purchases_increase = 0

        monthly_purchases_increase = f"{monthly_purchases_increase:.2f}%"

        if monthly_purchases > monthly_purchases_last_month:
            monthly_purchases_increase = f"+{monthly_purchases_increase}"
        elif monthly_purchases < monthly_purchases_last_month:
            monthly_purchases_increase = f"{monthly_purchases_increase}"

        # Laba Bersih
        daily_profit = daily_sales - daily_purchases
        daily_profit_yesterday = daily_sales_yesterday - daily_purchases_yesterday
        monthly_profit = monthly_sales - monthly_purchases
        monthly_profit_last_month = monthly_sales_last_month - monthly_purchases_last_month

        if daily_profit_yesterday != 0:
            daily_profit_increase = ((daily_profit - daily_profit_yesterday) / daily_profit_yesterday * 100)
        else:
            daily_profit_increase = 0

        daily_profit_increase = f"{daily_profit_increase:.2f}%"

        if daily_profit > daily_profit_yesterday:
            daily_profit_increase = f"{daily_profit_increase}"
        elif daily_profit < daily_profit_yesterday:
            daily_profit_increase = f"{daily_profit_increase}"

        if monthly_profit_last_month != 0:
            monthly_profit_increase = ((monthly_profit - monthly_profit_last_month) / monthly_profit_last_month * 100)
        else:
            monthly_profit_increase = 0

        monthly_profit_increase = f"{monthly_profit_increase:.2f}%"

        if monthly_profit > monthly_profit_last_month:
            monthly_profit_increase = f"+{monthly_profit_increase}"
        elif monthly_profit < monthly_profit_last_month:
            monthly_profit_increase = f"{monthly_profit_increase}"
        
        return render_template('beranda.html', nama_toko=nama_toko,
                           daily_sales=daily_sales, daily_increase=daily_increase,
                           monthly_sales=monthly_sales, monthly_increase=monthly_increase,
                           daily_purchases=daily_purchases, daily_purchases_increase=daily_purchases_increase,
                           monthly_purchases=monthly_purchases, monthly_purchases_increase=monthly_purchases_increase,
                           daily_profit=daily_profit, daily_profit_increase=daily_profit_increase,
                           monthly_profit=monthly_profit, monthly_profit_increase=monthly_profit_increase)
    return redirect(url_for('login'))

#Transaksi Penjualan
@app.route('/transaksi-list-penjualan')
def transaksi_list():
    if 'user_id' in session:
        user_id = session.get('user_id')
        role = session.get('role')
        user = User.query.get(user_id)
        if role == 'pemilik':
            transaksis = TransaksiPenjualan.query.filter_by(user_id=user.id).all()
        else:
            karyawan = Karyawan.query.filter_by(id=user.id).first()
            transaksis = TransaksiPenjualan.query.filter_by(user_id=karyawan.owner_id).all()
    return render_template('transaksi_penjualan/transaksi.html', transaksis=transaksis)

@app.route('/transaksi_baru', methods=['GET', 'POST'])
def transaksi_baru():
    if request.method == 'POST':
        user_id = session.get('user_id')
        karyawan_id = session.get('karyawan_id')
        role = session.get('role')
        total_amount = 0
        tanggal = request.form.get('tanggal')

        if not user_id:
            flash('User tidak ditemukan. Silakan login ulang.', 'danger')
            return redirect(url_for('login'))

        if role == 'pemilik':
            user = User.query.get(user_id)
            if not user:
                flash('User tidak valid.', 'danger')
                return redirect(url_for('login'))
        elif role == 'karyawan':
            karyawan = Karyawan.query.get(user_id)
            if not karyawan:
                flash('Karyawan tidak valid.', 'danger')
                return redirect(url_for('login'))
            user_id = karyawan.owner_id
        else:
            flash('Anda tidak memiliki hak akses untuk menambahkan transaksi.', 'danger')
            return redirect(url_for('transaksi_list'))

        try:
            transaksi = TransaksiPenjualan(user_id=user_id, karyawan_id=karyawan_id, total_harga=total_amount, tanggal=tanggal)
            db.session.add(transaksi)
            db.session.flush()

            # Process products
            products = request.form.getlist('products[][product_id]')
            quantities = request.form.getlist('products[][quantity]')

            details = []
            for i in range(len(products)):
                product_id = products[i]
                quantity = quantities[i]

                if not product_id or not quantity:
                    continue

                product_id = int(product_id)
                quantity = int(quantity)
                product_obj = Product.query.get(product_id)
                if not product_obj:
                    raise ValueError(f'Produk dengan ID {product_id} tidak ditemukan.')
                if product_obj.stock < quantity:
                    raise ValueError(f'Stok produk {product_obj.name} tidak mencukupi.')

                subtotal = product_obj.price * quantity
                total_amount += subtotal

                detail = DetailTransaksiPenjualan(transaksi_id=transaksi.id, product_id=product_id, jumlah=quantity, subtotal=subtotal)
                details.append(detail)
                product_obj.stock -= quantity
                db.session.add(product_obj)

            for detail in details:
                db.session.add(detail)

            transaksi.total_harga = total_amount
            db.session.commit()

            flash('Transaksi berhasil ditambahkan!', 'success')
            return redirect(url_for('transaksi_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('transaksi_baru'))

    products = Product.query.all()
    return render_template('transaksi_penjualan/transaksi_baru.html', products=products)

@app.route('/transaksi-penjualan/<int:transaksi_id>', methods=['GET', 'POST'])
def transaksi_detail(transaksi_id):
    transaksi = TransaksiPenjualan.query.get_or_404(transaksi_id)
    products = Product.query.all()
    details = transaksi.details_penjualan
    return render_template('transaksi_penjualan/detail_transaksi.html', transaksi=transaksi, details=details, products=products)

@app.route('/transaksi-penjualan/edit/<int:detail_id>', methods=['GET', 'POST'])
def edit_detail(detail_id):
    detail = DetailTransaksiPenjualan.query.get_or_404(detail_id)
    transaksi = TransaksiPenjualan.query.get(detail.transaksi_id)
    user_id = session.get('user_id') or session.get('owner_id')
    user = None
    
    if session.get('role') == 'pemilik':
        user = User.query.get(user_id)
    elif session.get('role') == 'karyawan':
        user = Karyawan.query.get(user_id)

    if not user:
        flash('User tidak valid.', 'danger')
        return redirect(url_for('login'))

    if (session.get('role') == 'karyawan' and transaksi.karyawan_id != user_id):
        flash('Anda tidak memiliki hak akses untuk mengedit detail transaksi ini.', 'danger')
        return redirect(url_for('transaksi_list'))

    original_jumlah = detail.jumlah
    product = Product.query.get(detail.product_id)

    if request.method == 'POST':
        try:
            new_jumlah = int(request.form['jumlah'])
            jumlah_diff = original_jumlah -new_jumlah
            detail.jumlah = new_jumlah
            detail.subtotal = product.price * new_jumlah
            product.stock += jumlah_diff
            transaksi.total_harga -= (jumlah_diff * product.price)

            db.session.commit()

            flash('Detail transaksi berhasil diperbarui!', 'success')
            return redirect(url_for('transaksi_detail', transaksi_id=detail.transaksi_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('edit_detail', detail_id=detail.id))

    return render_template('transaksi_penjualan/edit_detail_transaksi.html', detail=detail, product=product)

@app.route('/transaksi-penjualan/delete_detail/<int:detail_id>', methods=['POST'])
def delete_detail(detail_id):
    detail = DetailTransaksiPenjualan.query.get_or_404(detail_id)
    transaksi = TransaksiPenjualan.query.get(detail.transaksi_id)
    user_id = session.get('user_id') or session.get('owner_id')
    user = None

    if session.get('role') == 'pemilik':
        user = User.query.get(user_id)
    elif session.get('role') == 'karyawan':
        user = Karyawan.query.get(user_id)

    if not user:
        flash('User tidak valid.', 'danger')
        return redirect(url_for('login'))

    if (session.get('role') == 'karyawan' and transaksi.karyawan_id != user_id):
        flash('Anda tidak memiliki hak akses untuk menghapus detail transaksi ini.', 'danger')
        return redirect(url_for('transaksi_list'))

    try:
        product = Product.query.get(detail.product_id)
        product.stock += detail.jumlah
        transaksi.total_harga -= detail.subtotal

        db.session.delete(detail)
        db.session.commit()

        flash('Detail transaksi berhasil dihapus!', 'success')
        return redirect(url_for('transaksi_detail', transaksi_id=detail.transaksi_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('transaksi_detail', transaksi_id=detail.transaksi_id))

@app.route('/transaksi-penjualan/delete/<int:transaksi_id>', methods=['POST'])
def delete_transaksi(transaksi_id):
    transaksi = TransaksiPenjualan.query.get_or_404(transaksi_id)
    user_id = session.get('user_id') or session.get('owner_id')
    user = None

    if session.get('role') == 'pemilik':
        user = User.query.get(user_id)
    elif session.get('role') == 'karyawan':
        user = Karyawan.query.get(user_id)

    if not user:
        flash('User tidak valid.', 'danger')
        return redirect(url_for('login'))

    # Check if the user has the right role or is the owner of the transaction
    if (session.get('role') == 'karyawan' and transaksi.karyawan_id != user_id):
        flash('Anda tidak memiliki hak akses untuk menghapus transaksi ini.', 'danger')
        return redirect(url_for('transaksi_list'))

    try:
        # Return product stock to the original amount
        for detail in transaksi.details_penjualan:
            product = Product.query.get(detail.product_id)
            product.stock += detail.jumlah
            db.session.delete(detail)
        
        db.session.delete(transaksi)
        db.session.commit()

        flash('Transaksi berhasil dihapus!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')

    return redirect(url_for('transaksi_list'))

#Transaksi Pembelian
@app.route('/transaksi_list-pembelian')
def transaksi_list_pembelian():
    if 'user_id' in session:
        user_id = session.get('user_id')
        role = session.get('role')
        user = User.query.get(user_id)
        if role == 'pemilik':
            transaksis = TransaksiPembelian.query.filter_by(user_id=user.id).all()
        else:
            karyawan = Karyawan.query.filter_by(id=user.id).first()
            transaksis = TransaksiPembelian.query.filter_by(user_id=karyawan.owner_id).all()
    return render_template('transaksi_pembelian/transaksi.html', transaksis=transaksis)

@app.route('/transaksi-pembelian_baru', methods=['GET', 'POST'])
def transaksi_pembelian_baru():
    if request.method == 'POST':
        user_id = session.get('user_id')
        karyawan_id = session.get('karyawan_id')
        role = session.get('role')
        total_amount = 0
        tanggal = request.form.get('tanggal')

        if not user_id:
            flash('User tidak ditemukan. Silakan login ulang.', 'danger')
            return redirect(url_for('login'))

        if role == 'pemilik':
            user = User.query.get(user_id)
            if not user:
                flash('User tidak valid.', 'danger')
                return redirect(url_for('login'))
        elif role == 'karyawan':
            karyawan = Karyawan.query.get(user_id)
            if not karyawan:
                flash('Karyawan tidak valid.', 'danger')
                return redirect(url_for('login'))
            user_id = karyawan.owner_id
        else:
            flash('Anda tidak memiliki hak akses untuk menambahkan transaksi.', 'danger')
            return redirect(url_for('transaksi_list_pembelian'))

        try:
            transaksi = TransaksiPembelian(user_id=user_id, karyawan_id=karyawan_id, total_harga=total_amount, tanggal=tanggal)
            db.session.add(transaksi)
            db.session.flush()

            # Process products
            products = request.form.getlist('products[][product_id]')
            quantities = request.form.getlist('products[][quantity]')

            details = []
            for i in range(len(products)):
                product_id = products[i]
                quantity = quantities[i]

                if not product_id or not quantity:
                    continue

                product_id = int(product_id)
                quantity = int(quantity)
                product_obj = Product.query.get(product_id)
                if not product_obj:
                    raise ValueError(f'Produk dengan ID {product_id} tidak ditemukan.')

                subtotal = product_obj.harga_beli * quantity
                total_amount += subtotal

                detail = DetailTransaksiPembelian(transaksi_id=transaksi.id, product_id=product_id, jumlah=quantity, subtotal=subtotal)
                details.append(detail)
                product_obj.stock += quantity
                db.session.add(product_obj)

            for detail in details:
                db.session.add(detail)

            transaksi.total_harga = total_amount
            db.session.commit()

            flash('Transaksi berhasil ditambahkan!', 'success')
            return redirect(url_for('transaksi_list_pembelian'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('transaksi_baru'))

    products = Product.query.all()
    return render_template('transaksi_pembelian/transaksi_baru.html', products=products)

@app.route('/transaksi-pembelian/<int:transaksi_id>', methods=['GET', 'POST'])
def transaksi_detail_pembelian(transaksi_id):
    transaksi = TransaksiPembelian.query.get_or_404(transaksi_id)
    products = Product.query.all()
    details = transaksi.details_pembelian
    return render_template('transaksi_pembelian/detail_transaksi.html', transaksi=transaksi, details=details, products=products)

@app.route('/transaksi-pembelian/edit/<int:detail_id>', methods=['GET', 'POST'])
def edit_detail_pembelian(detail_id):
    detail = DetailTransaksiPembelian.query.get_or_404(detail_id)
    transaksi = TransaksiPembelian.query.get(detail.transaksi_id)
    user_id = session.get('user_id') or session.get('owner_id')
    user = None
    
    if session.get('role') == 'pemilik':
        user = User.query.get(user_id)
    elif session.get('role') == 'karyawan':
        user = Karyawan.query.get(user_id)

    if not user:
        flash('User tidak valid.', 'danger')
        return redirect(url_for('login'))

    if (session.get('role') == 'karyawan' and transaksi.karyawan_id != user_id):
        flash('Anda tidak memiliki hak akses untuk mengedit detail transaksi ini.', 'danger')
        return redirect(url_for('transaksi_list_pembelian'))

    original_jumlah = detail.jumlah
    product = Product.query.get(detail.product_id)

    if request.method == 'POST':
        try:
            new_jumlah = int(request.form['jumlah'])
            jumlah_diff = original_jumlah -new_jumlah
            detail.jumlah = new_jumlah
            detail.subtotal = product.harga_beli * new_jumlah
            product.stock -= jumlah_diff
            transaksi.total_harga -= (jumlah_diff * product.harga_beli)

            db.session.commit()

            flash('Detail transaksi berhasil diperbarui!', 'success')
            return redirect(url_for('transaksi_detail_pembelian', transaksi_id=detail.transaksi_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('edit_detail_pembelian', detail_id=detail.id))

    return render_template('transaksi_pembelian/edit_detail_transaksi.html', detail=detail, product=product)
    
@app.route('/transaksi-pembelian/delete_detail/<int:detail_id>', methods=['POST'])
def delete_detail_pembelian(detail_id):
    detail = DetailTransaksiPembelian.query.get_or_404(detail_id)
    transaksi = TransaksiPembelian.query.get(detail.transaksi_id)
    user_id = session.get('user_id') or session.get('owner_id')
    user = None

    if session.get('role') == 'pemilik':
        user = User.query.get(user_id)
    elif session.get('role') == 'karyawan':
        user = Karyawan.query.get(user_id)

    if not user:
        flash('User tidak valid.', 'danger')
        return redirect(url_for('login'))

    if (session.get('role') == 'karyawan' and transaksi.karyawan_id != user_id):
        flash('Anda tidak memiliki hak akses untuk menghapus detail transaksi ini.', 'danger')
        return redirect(url_for('transaksi_list_pembelian'))

    try:
        product = Product.query.get(detail.product_id)
        product.stock -= detail.jumlah
        transaksi.total_harga -= detail.subtotal

        db.session.delete(detail)
        db.session.commit()

        flash('Detail transaksi berhasil dihapus!', 'success')
        return redirect(url_for('transaksi_detail_pembelian', transaksi_id=detail.transaksi_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('transaksi_detail_pembelian', transaksi_id=detail.transaksi_id))

@app.route('/transaksi-pembelian/delete/<int:transaksi_id>', methods=['POST'])
def delete_transaksi_pembelian(transaksi_id):
    transaksi = TransaksiPembelian.query.get_or_404(transaksi_id)
    user_id = session.get('user_id') or session.get('owner_id')
    user = None

    if session.get('role') == 'pemilik':
        user = User.query.get(user_id)
    elif session.get('role') == 'karyawan':
        user = Karyawan.query.get(user_id)

    if not user:
        flash('User tidak valid.', 'danger')
        return redirect(url_for('login'))

    if (session.get('role') == 'karyawan' and transaksi.karyawan_id != user_id):
        flash('Anda tidak memiliki hak akses untuk menghapus transaksi ini.', 'danger')
        return redirect(url_for('transaksi_list_pembelian'))

    try:
        for detail in transaksi.details_pembelian:
            product = Product.query.get(detail.product_id)
            if product:
                product.stock -= detail.jumlah
                db.session.delete(detail)
        
        db.session.delete(transaksi)
        db.session.commit()

        flash('Transaksi berhasil dihapus!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('transaksi_list_pembelian'))

#Produk
@app.route('/product_search', methods=['GET'])
def product_search():
    query = request.args.get('q', '')
    if 'user_id' not in session:
        return jsonify([]), 403  # Return an empty list and forbidden status if user is not logged in

    user_id = session.get('user_id')
    role = session.get('role')
    
    if role == 'pemilik':
        user = User.query.get(user_id)
        if user:
            products = Product.query.filter(Product.name.ilike(f'%{query}%'), Product.user_id == user.id).all()
        else:
            return jsonify([]), 404  # User not found
    else:
        karyawan = Karyawan.query.filter_by(id=user_id).first()
        if karyawan:
            products = Product.query.filter(Product.name.ilike(f'%{query}%'), Product.user_id == karyawan.owner_id).all()
        else:
            return jsonify([]), 404  # Karyawan not found

    results = [
        {'id': product.id, 'name': product.name, 'stock': product.stock}
        for product in products
    ]
    return jsonify(results)

@app.route("/produk")
def produk():
    if 'user_id' in session:
        user_id = session.get('user_id')
        role = session.get('role')
        user = User.query.get(user_id)
        if role == 'pemilik':
            products = Product.query.filter_by(user_id=user.id).all()
        else:
            karyawan = Karyawan.query.filter_by(id=user.id).first()
            products = Product.query.filter_by(user_id=karyawan.owner_id).all()
    # products = Product.query.all()
    return render_template('produk/produk.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('produk/detail_produk.html', product=product)

@app.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    user_id = session.get('user_id') or session.get('owner_id')
    user = None

    if session.get('role') == 'pemilik':
        user = User.query.get(user_id)
    elif session.get('role') == 'karyawan':
        user = Karyawan.query.get(user_id)

    if not user:
        flash('User tidak valid.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            product.name = request.form['name']
            product.description = request.form['description']
            product.harga_beli = float(request.form['harga_beli'])
            product.price = float(request.form['price'])
            product.category = request.form['category']

            if 'image' in request.files:
                image_file = request.files['image']
                if image_file.filename != '':
                    image_filename = secure_filename(image_file.filename)
                    image_file.save(os.path.join('static/product_images', image_filename))
                    product.image = image_filename

            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('product_detail', product_id=product.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('edit_product', product_id=product.id))

    return render_template('produk/edit_produk.html', product=product)

@app.route('/product/new', methods=['GET', 'POST'])
def new_product():
    if 'role' in session:
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            harga_beli = float(request.form['harga_beli'])
            price = float(request.form['price'])
            category = request.form['category']
            image_file = request.files['image']
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join('static/product_images', image_filename))

            new_product = Product(name=name, description=description, harga_beli=harga_beli, price=price, category=category, image=image_filename, user_id=session['user_id'])
            db.session.add(new_product)
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('produk'))

    return render_template('produk/produk_baru.html')

@app.route('/product/delete/<int:product_id>', methods=['GET', 'POST'])
def delete_product(product_id):
    if request.method == 'POST':
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    return redirect(url_for('produk'))

@app.route('/search')
def search_product():
    # query = request.args.get('query')
    # products = Product.query.filter(Product.name.like(f'%{query}%')).all()
    query = request.args.get('query', '')
    products = []

    if 'user_id' in session:
        user_id = session.get('user_id')
        role = session.get('role')
        user = User.query.get(user_id)

        if role == 'pemilik':
            products = Product.query.filter(
                Product.user_id == user.id,
                Product.name.like(f'%{query}%')
            ).all()
        else:
            karyawan = Karyawan.query.filter_by(id=user.id).first()
            products = Product.query.filter(
                Product.user_id == karyawan.owner_id,
                Product.name.like(f'%{query}%')
            ).all()
    return render_template('produk/produk.html', products=products)

#Pengaturan
@app.route('/pengaturan')
def pengaturan():
    user_id = session.get('user_id')
    if 'role' in session:
        if session['role'] == 'pemilik':
            user = User.query.get_or_404(user_id)
            user_id = user.id
            # Handle 'pemilik' role logic
        else:
            user = Karyawan.query.get_or_404(user_id)
            user_id = user.id
            # Handle other roles logic
        # Continue processing for settings based on user role
    else:
        # Handle case where 'role' is not set in session
        # This could be redirecting to a login page or displaying an error message
        return 'Role not found in session. Please log in.'

    # Additional logic for settings page
    return render_template('pengaturan/pengaturan.html', user=user)

@app.route('/ubah-password', methods=['GET', 'POST'])
def ubah_password():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    role = session.get('role')
    if role == 'pemilik':
        user = User.query.get_or_404(user_id)
    elif role == 'karyawan':
        user = Karyawan.query.get_or_404(user_id)
    else:
        return 'Role not found in session. Please log in.', 401

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if not check_password_hash(user.password, current_password):
            flash('Password saat ini salah!', 'danger')
        elif new_password != confirm_password:
            flash('Password baru tidak cocok!', 'danger')
        else:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            return redirect(url_for('pengaturan'))

    return render_template('pengaturan/ubah_password.html', user=user)

@app.route('/profile/<int:user_id>')
def profile(user_id):
    user_id = session.get('user_id')
    if 'role' in session:
        if session['role'] == 'pemilik' :
            user = User.query.get_or_404(user_id)
        else:
            user = Karyawan.query.get_or_404(user_id)
    else:
        return 'Role not found in session. Please log in.'

    return render_template('pengaturan/profile.html', user=user)

@app.route('/profile/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_profile(user_id):
    user_id = session.get('user_id')
    if 'role' in session:
        if session['role'] == 'pemilik' :
            user = User.query.get_or_404(user_id)
            if request.method == 'POST':
                user.nama_toko = request.form['nama_toko']
                user.nama_pemilik = request.form['nama_pemilik']
                user.username = request.form['username']
                user.email = request.form['email']
                user.phone = request.form['phone']
                if 'profile_pic' in request.files:
                    image_file = request.files['profile_pic']
                    if image_file.filename != '':
                        image_filename = secure_filename(image_file.filename)
                        image_file.save(os.path.join(app.config['FOLDER_PROFILE_P'], image_filename))
                        user.profile_pic = image_filename
                db.session.commit()
                flash('Profil diperbarui!', 'success')
                return redirect(url_for('profile', user_id=user.id))
        else:
            user = Karyawan.query.get_or_404(user_id)
            if request.method == 'POST':
                user.nama_karyawan = request.form['nama_karyawan']
                user.username = request.form['username']
                user.email = request.form['email']
                user.phone = request.form['phone']
                if 'profile_pic' in request.files:
                    image_file = request.files['profile_pic']
                    if image_file.filename != '':
                        image_filename = secure_filename(image_file.filename)
                        image_file.save(os.path.join(app.config['FOLDER_PROFILE_P'], image_filename))
                        user.profile_pic = image_filename
                db.session.commit()
                flash('Profil diperbarui!', 'success')
                return redirect(url_for('profile', user_id=user.id))
    else:
        return 'Role not found in session. Please log in.'
    
    return render_template('pengaturan/edit_profile.html', user=user)

#Karyawan
@app.route('/daftar-karyawan')
def daftar_karyawan():
    if 'user_id' not in session or session['role'] != 'pemilik':
        return redirect(url_for('login'))
    karyawan = Karyawan.query.filter_by(owner_id=session['user_id']).all()
    return render_template('karyawan/daftar_karyawan.html', karyawan=karyawan)

@app.route('/tambah-karyawan', methods=['GET', 'POST'])
def tambah_karyawan():
    if 'user_id' not in session or session['role'] != 'pemilik':
        return redirect(url_for('login'))
    if request.method == 'POST':
        nama_karyawan = request.form['namaK']
        username = request.form['usernameK']
        password = generate_password_hash(request.form['passwordK'])
        email = request.form['emailK']
        phone = request.form['phoneK']
        profile_pic = request.files['profile_pic_k']
        image_filename = secure_filename(profile_pic.filename)
        profile_pic.save(os.path.join(app.config['FOLDER_PROFILE_P'], image_filename))

        karyawan_baru = Karyawan(
            nama_karyawan=nama_karyawan,
            username=username, 
            password=password, 
            email=email, 
            phone=phone, 
            profile_pic=image_filename, 
            owner_id=session['user_id']
        )
        db.session.add(karyawan_baru)
        db.session.commit()
        return redirect(url_for('daftar_karyawan'))
    return render_template('karyawan/tambah_karyawan.html')

@app.route('/detail-karyawan/<int:karyawan_id>')
def detail_karyawan(karyawan_id):
    karyawan = Karyawan.query.get_or_404(karyawan_id)
    return render_template('karyawan/detail_karyawan.html', karyawan=karyawan)

@app.route('/edit-karyawan/<int:karyawan_id>', methods=['GET', 'POST'])
def edit_karyawan(karyawan_id):
    if 'user_id' not in session or session['role'] != 'pemilik':
        return redirect(url_for('login'))
    karyawan = Karyawan.query.get_or_404(karyawan_id)
    if request.method == 'POST':
        karyawan.nama_karyawan = request.form['namaK']
        karyawan.username = request.form['usernameK']
        karyawan.email = request.form['emailK']
        karyawan.phone = request.form['phoneK']

        if 'profile_pic_k' in request.files:
            image_file = request.files['profile_pic_k']
            if image_file.filename != '':
                image_filename = secure_filename(image_file.filename)
                image_file.save(os.path.join(app.config['FOLDER_PROFILE_P'], image_filename))
                karyawan.profile_pic = image_filename
                
        db.session.commit()
        return redirect(url_for('detail_karyawan', karyawan_id=karyawan.id))
    return render_template('karyawan/edit_data_karyawan.html', karyawan=karyawan)

@app.route('/hapus-karyawan/<int:karyawan_id>', methods=['GET', 'POST'])
def hapus_karyawan(karyawan_id):
    if 'user_id' not in session or session['role'] != 'pemilik':
        return redirect(url_for('login'))
    if request.method == 'POST':
        karyawan = Karyawan.query.get_or_404(karyawan_id)
        db.session.delete(karyawan)
        db.session.commit()
    return redirect(url_for('daftar_karyawan'))

if __name__ == '__main__':
    app.run(debug=True)

