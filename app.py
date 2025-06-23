from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, Numeric, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from decimal import Decimal, InvalidOperation
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
import io
import base64
import matplotlib.pyplot as plt

#конфигурации
app = Flask(__name__)
app.config['SECRET_KEY'] = 'swagaa3f4c8e9b2d507f61e8c0a7b5d2e1f4a9b3c8d0e7f6a1b2c3'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Web.db'
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


#модели бд
class User(UserMixin, db.Model):
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Username = Column(Text, nullable=False, unique=True)
    Email = Column(Text, nullable=False, unique=True)
    Password = Column(Text, nullable=False)

    accounts = relationship("Account", back_populates="user")
    budgets = relationship("Budget", back_populates="user")
    expenses = relationship("Expense", back_populates="user")
    incomes = relationship("Income", back_populates="user")

    def get_id(self):
        return str(self.Id)


class Account(db.Model):
    Id = Column(Integer, primary_key=True, autoincrement=True)
    IdUser = Column(Integer, ForeignKey('user.Id'), nullable=False)
    Name = Column(Text, nullable=False)
    Balance = Column(Numeric(10, 2), nullable=False, default=0)
    CreatedAt = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="accounts")


class Budget(db.Model):
    Id = Column(Integer, primary_key=True, autoincrement=True)
    IdUser = Column(Integer, ForeignKey('user.Id'), nullable=False)
    Name = Column(Text, nullable=False)
    Amount = Column(Numeric(10, 2), nullable=False)
    Month = Column(Integer, nullable=False)
    Year = Column(Integer, nullable=False)

    user = relationship("User", back_populates="budgets")


class Category(db.Model):
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(Text, nullable=False, unique=True)
    Type = Column(Text, nullable=False) 


class Income(db.Model):
    Id = Column(Integer, primary_key=True, autoincrement=True)
    IdUser = Column(Integer, ForeignKey('user.Id'), nullable=False)
    IdCategory = Column(Integer, ForeignKey('category.Id'), nullable=False)
    Amount = Column(Numeric(10, 2), nullable=False)
    Date = Column(DateTime, nullable=False, default=datetime.utcnow)
    Note = Column(Text)

    user = relationship("User", back_populates="incomes")
    category = relationship("Category")  

class Expense(db.Model):
    Id = Column(Integer, primary_key=True, autoincrement=True)
    IdUser = Column(Integer, ForeignKey('user.Id'), nullable=False)
    IdCategory = Column(Integer, ForeignKey('category.Id'), nullable=False)
    Amount = Column(Numeric(10, 2), nullable=False)
    Date = Column(DateTime, nullable=False, default=datetime.utcnow)
    Note = Column(Text)

    user = relationship("User", back_populates="expenses")
    category = relationship("Category")  # связь с таблицей категорий


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')
#модели


#маршруты
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return redirect(url_for('login'))


@app.route("/index")
@login_required
def index():
    return render_template('index.html')


@app.route("/income", methods=['GET', 'POST'])
@login_required
def income():
    categories = Category.query.filter_by(Type='income').all()
    incomes = Income.query.filter_by(IdUser=current_user.Id).order_by(Income.Date.desc()).all()

    if request.method == 'POST':
        try:
            category_id = request.form.get('category_id')
            amount_str = request.form.get('amount')
            date_str = request.form.get('date')
            note = request.form.get('note', '')

            if not category_id:
                flash('Выберите категорию.', 'error')
                return redirect(url_for('income'))

            try:
                amount = Decimal(amount_str)
            except InvalidOperation:
                flash('Введите корректную сумму.', 'error')
                return redirect(url_for('income'))

            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                flash('Неверный формат даты. Используйте ГГГГ-ММ-ДД.', 'error')
                return redirect(url_for('income'))

            income = Income(
                IdUser=current_user.Id,
                IdCategory=int(category_id),
                Amount=amount,
                Date=date_obj,
                Note=note
            )
            db.session.add(income)
            db.session.commit()
            flash('Доход успешно добавлен!', 'success')
            return redirect(url_for('income'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении дохода: {str(e)}', 'error')

    return render_template('income.html', categories=categories, incomes=incomes)


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            balance_str = request.form.get('balance', '0')
            try:
                balance = Decimal(balance_str)
            except InvalidOperation:
                flash("Введите корректный баланс.", "error")
                return redirect(url_for('account'))

            account = Account(
                IdUser=current_user.Id,
                Name=name,
                Balance=balance
            )
            db.session.add(account)
            db.session.commit()
            flash('Счет успешно создан!', 'success')
            return redirect(url_for('account'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании счета: {str(e)}', 'error')

    accounts = Account.query.filter_by(IdUser=current_user.Id).all()
    return render_template('account.html', accounts=accounts)


@app.route("/budget", methods=['GET', 'POST'])
@login_required
def budget():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            amount_str = request.form.get('amount')
            month = int(request.form.get('month'))
            year = int(request.form.get('year'))

            try:
                amount = Decimal(amount_str)
            except InvalidOperation:
                flash("Введите корректную сумму бюджета.", "error")
                return redirect(url_for('budget'))

            budget = Budget(
                IdUser=current_user.Id,
                Name=name,
                Amount=amount,
                Month=month,
                Year=year
            )
            db.session.add(budget)
            db.session.commit()
            flash('Бюджет успешно создан!', 'success')
            return redirect(url_for('budget'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании бюджета: {str(e)}', 'error')

    budgets = Budget.query.filter_by(IdUser=current_user.Id).all()
    return render_template('budget.html', budgets=budgets)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(Email=request.form['email']).first()
        if user and check_password_hash(user.Password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash("Неверный email или пароль", "error")
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                Username=form.username.data,
                Email=form.email.data,
                Password=generate_password_hash(form.password.data)
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Регистрация прошла успешно!", "success")
            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash("Пользователь с таким email уже существует", "error")
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при регистрации: {str(e)}", "error")
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.template_filter('month_name')
def month_name_filter(month_num):
    months = [
        "", "Январь", "Февраль", "Март", "Апрель",
        "Май", "Июнь", "Июль", "Август",
        "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    return months[month_num] if 1 <= month_num <= 12 else ""


@app.route("/expenses", methods=['GET', 'POST'])
@login_required
def expenses():
    categories = Category.query.filter_by(Type='expense').all()
    expenses = Expense.query.filter_by(IdUser=current_user.Id).order_by(Expense.Date.desc()).all()

    if request.method == 'POST':
        try:
            category_id = request.form.get('category_id')
            amount_str = request.form.get('amount')
            date_str = request.form.get('date')
            note = request.form.get('note', '')

            if not category_id:
                flash('Выберите категорию.', 'error')
                return redirect(url_for('expenses'))

            try:
                amount = Decimal(amount_str)
            except InvalidOperation:
                flash('Введите корректную сумму.', 'error')
                return redirect(url_for('expenses'))

            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                flash('Неверный формат даты. Используйте ГГГГ-ММ-ДД.', 'error')
                return redirect(url_for('expenses'))

            expense = Expense(
                IdUser=current_user.Id,
                IdCategory=int(category_id),
                Amount=amount,
                Date=date_obj,
                Note=note
            )
            db.session.add(expense)
            db.session.commit()
            flash('Расход успешно добавлен!', 'success')
            return redirect(url_for('expenses'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении расхода: {str(e)}', 'error')

    return render_template('expenses.html', categories=categories, expenses=expenses)
#маршруты

#инициализация бд

def initialize_database():
    with app.app_context():
        if not Category.query.first():
            expense_categories = ["Продукты", "Транспорт", "Жилье", "Развлечения", "Здоровье", "Одежда", "Образование", "Другое"]
            income_categories = ["Зарплата", "Подарки", "Инвестиции"]

            for cat in expense_categories:
                db.session.add(Category(Name=cat, Type='expense'))

            for cat in income_categories:
                db.session.add(Category(Name=cat, Type='income'))

            db.session.commit()
#инициализация бд

#ЗАПУСК
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        initialize_database()
    app.run(host='0.0.0.0', port=5000, debug=True)

