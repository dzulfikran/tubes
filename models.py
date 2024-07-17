from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_toko = db.Column(db.String(100), nullable=False)
    nama_pemilik = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    profile_pic = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Karyawan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_karyawan = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    profile_pic = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref=db.backref('karyawan', lazy=True))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    harga_beli = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    category = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (
        db.CheckConstraint('price >= 0', name='check_price_nonnegative'),
        db.CheckConstraint('stock >= 0', name='check_stock_nonnegative'),
    )

class TransaksiPenjualan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.Date, nullable=False)
    total_harga = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    user = db.relationship('User', backref=db.backref('transaksis_penjualan', lazy=True))
    karyawan_id = db.Column(db.Integer, db.ForeignKey('karyawan.id'), nullable=True, index=True)
    karyawan = db.relationship('Karyawan', backref=db.backref('transaksis_penjualan', lazy=True))

class DetailTransaksiPenjualan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaksi_id = db.Column(db.Integer, db.ForeignKey('transaksi_penjualan.id'), nullable=False, index=True)
    transaksi = db.relationship('TransaksiPenjualan', backref=db.backref('details_penjualan', lazy=True))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    product = db.relationship('Product', backref=db.backref('details_penjualan', lazy=True))
    jumlah = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.CheckConstraint('jumlah >= 0', name='check_jumlah_nonnegative'),
        db.CheckConstraint('subtotal >= 0', name='check_subtotal_nonnegative'),
    )

class TransaksiPembelian(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.Date, nullable=False)
    total_harga = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    user = db.relationship('User', backref=db.backref('transaksis_pembelian', lazy=True))
    karyawan_id = db.Column(db.Integer, db.ForeignKey('karyawan.id'), nullable=True, index=True)
    karyawan = db.relationship('Karyawan', backref=db.backref('transaksis_pembelian', lazy=True))

class DetailTransaksiPembelian(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaksi_id = db.Column(db.Integer, db.ForeignKey('transaksi_pembelian.id'), nullable=False, index=True)
    transaksi = db.relationship('TransaksiPembelian', backref=db.backref('details_pembelian', lazy=True))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    product = db.relationship('Product', backref=db.backref('details_pembelian', lazy=True))
    jumlah = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.CheckConstraint('jumlah >= 0', name='check_jumlah_nonnegative'),
        db.CheckConstraint('subtotal >= 0', name='check_subtotal_nonnegative'),
    )
