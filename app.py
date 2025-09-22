from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SelectField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, EqualTo, ValidationError
from datetime import datetime
import os
import logging

# Set up logging to debug database operations
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+mysqlconnector://krishna:mysql%40123@localhost:3306/crowdfund"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_timeout': 20,
    'pool_size': 10,
    'max_overflow': 20
}

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # Increased length for MySQL
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='creator', lazy=True, cascade='all, delete-orphan')
    contributions = db.relationship('Contribution', backref='contributor', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    funding_goal = db.Column(db.DECIMAL(10, 2), nullable=False)  # Better for currency in MySQL
    comments = db.Column(db.Text, default='')  # Comments as JSON string or simple text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # Relationships
    contributions = db.relationship('Contribution', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def get_total_raised(self):
        """Calculate total amount raised for this project"""
        total = sum([float(contrib.amount) for contrib in self.contributions])
        return total
    
    def get_progress_percentage(self):
        """Calculate funding progress as percentage"""
        if float(self.funding_goal) <= 0:
            return 0
        total_raised = self.get_total_raised()
        progress = (total_raised / float(self.funding_goal)) * 100
        return min(progress, 100)  # Cap at 100%
    
    def get_contribution_count(self):
        """Get number of contributions for this project"""
        return len(self.contributions)
    
    def get_comments_list(self):
        """Parse comments from JSON string to list"""
        if not self.comments:
            return []
        try:
            import json
            return json.loads(self.comments)
        except:
            return []
    
    def add_comment(self, username, comment_text):
        """Add a new comment to the project"""
        import json
        comments_list = self.get_comments_list()
        new_comment = {
            'username': username,
            'comment': comment_text,
            'created_at': datetime.utcnow().isoformat()
        }
        comments_list.append(new_comment)
        self.comments = json.dumps(comments_list)
    
    def __repr__(self):
        return f'<Project {self.title}>'

class Contribution(db.Model):
    __tablename__ = 'contributions'
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.DECIMAL(10, 2), nullable=False)  # Better for currency in MySQL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    def __repr__(self):
        return f'<Contribution ${self.amount} to Project {self.project_id}>'

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=4, max=20, message='Username must be between 4 and 20 characters.')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please choose a different email.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired()
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ProjectForm(FlaskForm):
    title = StringField('Project Title', validators=[
        DataRequired(),
        Length(min=5, max=200, message='Title must be between 5 and 200 characters.')
    ])
    description = TextAreaField('Description', validators=[
        DataRequired(),
        Length(min=20, message='Description must be at least 20 characters long.')
    ])
    funding_goal = FloatField('Funding Goal ($)', validators=[
        DataRequired(),
        NumberRange(min=1, max=1000000, message='Funding goal must be between $1 and $1,000,000.')
    ])
    category = SelectField('Category', validators=[
        DataRequired()
    ], coerce=int)
    submit = SubmitField('Create Project')

class ContributionForm(FlaskForm):
    amount = FloatField('Contribution Amount ($)', validators=[
        DataRequired(),
        NumberRange(min=1, max=10000, message='Contribution must be between $1 and $10,000.')
    ])
    submit = SubmitField('Contribute')

class CommentForm(FlaskForm):
    comment = TextAreaField('Add a Comment', validators=[
        DataRequired(),
        Length(min=5, max=500, message='Comment must be between 5 and 500 characters.')
    ])
    submit = SubmitField('Post Comment')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom Jinja2 filter for datetime parsing
@app.template_filter('strftime')
def datetime_filter(s, format='%B %d, %Y at %I:%M %p'):
    """Convert datetime string to formatted string"""
    try:
        if isinstance(s, str):
            # Parse ISO format datetime string
            if 'T' in s:
                dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(s)
        else:
            dt = s
        return dt.strftime(format)
    except:
        return s

# Routes
@app.route('/')
def home():
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(6).all()
    return render_template('home.html', projects=recent_projects)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered. Please use a different email.', 'danger')
            return render_template('register.html', form=form)
        
        # Create new user
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data)
            )
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"New user registered: {user.username} ({user.email})")
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        flash('Invalid email or password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/projects')
def projects():
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '', type=str)
    
    query = Project.query
    
    # Apply search filter
    if search_query:
        query = query.filter(
            db.or_(
                Project.title.contains(search_query),
                Project.description.contains(search_query)
            )
        )
    
    # Apply category filter
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    projects = query.order_by(Project.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False
    )
    
    categories = Category.query.all()
    return render_template('projects.html', 
                         projects=projects, 
                         categories=categories, 
                         selected_category=category_id,
                         search_query=search_query)

@app.route('/project/<int:id>')
def project_detail(id):
    project = Project.query.get_or_404(id)
    contribution_form = ContributionForm()
    comment_form = CommentForm()
    contributions = Contribution.query.filter_by(project_id=id).order_by(Contribution.created_at.desc()).limit(10).all()
    
    # Calculate progress
    total_raised = db.session.query(db.func.sum(Contribution.amount)).filter_by(project_id=id).scalar() or 0
    progress_percentage = min((total_raised / project.funding_goal) * 100, 100) if project.funding_goal > 0 else 0
    
    # Get comments
    comments = project.get_comments_list()
    
    return render_template('project_detail.html', 
                         project=project, 
                         contribution_form=contribution_form,
                         comment_form=comment_form,
                         contributions=contributions,
                         total_raised=total_raised,
                         progress_percentage=progress_percentage,
                         comments=comments)

@app.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    form = ProjectForm()
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        project = Project(
            title=form.title.data,
            description=form.description.data,
            funding_goal=form.funding_goal.data,
            category_id=form.category.data,
            user_id=current_user.id
        )
        db.session.add(project)
        db.session.commit()
        
        flash('Project created successfully!', 'success')
        return redirect(url_for('project_detail', id=project.id))
    
    return render_template('create_project.html', form=form)

@app.route('/contribute/<int:project_id>', methods=['POST'])
@login_required
def contribute(project_id):
    project = Project.query.get_or_404(project_id)
    form = ContributionForm()
    
    if form.validate_on_submit():
        try:
            contribution = Contribution(
                amount=form.amount.data,
                user_id=current_user.id,
                project_id=project_id
            )
            db.session.add(contribution)
            db.session.commit()
            
            logger.info(f"New contribution: ${form.amount.data} by {current_user.username} to project {project_id}")
            flash(f'Thank you for your contribution of ${form.amount.data}!', 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating contribution: {str(e)}")
            flash('Contribution failed. Please try again.', 'danger')
    else:
        flash('Invalid contribution amount.', 'danger')
    
    return redirect(url_for('project_detail', id=project_id))

@app.route('/add_comment/<int:project_id>', methods=['POST'])
@login_required
def add_comment(project_id):
    project = Project.query.get_or_404(project_id)
    form = CommentForm()
    
    if form.validate_on_submit():
        project.add_comment(current_user.username, form.comment.data)
        db.session.commit()
        flash('Comment added successfully!', 'success')
    else:
        flash('Invalid comment. Please check your input.', 'danger')
    
    return redirect(url_for('project_detail', id=project_id))

@app.route('/my_projects')
@login_required
def my_projects():
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()
    
    # Calculate totals for each project
    project_data = []
    for project in projects:
        total_raised = db.session.query(db.func.sum(Contribution.amount)).filter_by(project_id=project.id).scalar() or 0
        contribution_count = Contribution.query.filter_by(project_id=project.id).count()
        project_data.append({
            'project': project,
            'total_raised': total_raised,
            'contribution_count': contribution_count
        })
    
    return render_template('my_projects.html', project_data=project_data)

@app.route('/project/<int:project_id>/contributions')
@login_required
def project_contributions(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Check if user owns this project
    if project.user_id != current_user.id and not current_user.is_admin:
        flash('You can only view contributions for your own projects.', 'danger')
        return redirect(url_for('projects'))
    
    contributions = Contribution.query.filter_by(project_id=project_id).order_by(Contribution.created_at.desc()).all()
    total_raised = db.session.query(db.func.sum(Contribution.amount)).filter_by(project_id=project_id).scalar() or 0
    
    return render_template('project_contributions.html', 
                         project=project, 
                         contributions=contributions,
                         total_raised=total_raised)

@app.route('/admin')
@login_required
def admin_dashboard():
    # Check if user is admin (you can modify this logic)
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('home'))
    
    total_projects = Project.query.count()
    total_users = User.query.count()
    total_contributions = Contribution.query.count()
    total_raised = db.session.query(db.func.sum(Contribution.amount)).scalar() or 0
    
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(10).all()
    recent_contributions = Contribution.query.order_by(Contribution.created_at.desc()).limit(10).all()
    
    return render_template('admin_dashboard.html',
                         total_projects=total_projects,
                         total_users=total_users,
                         total_contributions=total_contributions,
                         total_raised=total_raised,
                         recent_projects=recent_projects,
                         recent_contributions=recent_contributions)

def create_default_data():
    """Create default categories and admin user"""
    try:
        # Create categories if they don't exist
        categories = ['Technology', 'Education', 'Art', 'Health', 'Environment', 'Community']
        for cat_name in categories:
            if not Category.query.filter_by(name=cat_name).first():
                category = Category(name=cat_name, description=f'{cat_name} projects')
                db.session.add(category)
                logger.info(f"Created category: {cat_name}")
        
        # Create admin user if it doesn't exist
        admin_email = 'admin@crowdfund.com'
        if not User.query.filter_by(email=admin_email).first():
            admin = User(
                username='admin',
                email=admin_email,
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            logger.info(f"Created admin user: {admin_email}")
        
        db.session.commit()
        logger.info("Default data creation completed")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating default data: {str(e)}")

# Add route to check database connectivity
@app.route('/debug/db-info')
def debug_db_info():
    """Debug route to check database connection and data"""
    if not current_user.is_authenticated or not current_user.is_admin:
        return "Access denied", 403
    
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        
        # Get counts
        user_count = User.query.count()
        project_count = Project.query.count()
        contribution_count = Contribution.query.count()
        category_count = Category.query.count()
        
        # Get all users
        users = User.query.all()
        user_list = [f"{u.id}: {u.username} ({u.email}) - Admin: {u.is_admin}" for u in users]
        
        # Get all contributions
        contributions = Contribution.query.all()
        contrib_list = [f"ID: {c.id}, Amount: ${c.amount}, User: {c.user_id}, Project: {c.project_id}" for c in contributions]
        
        return f"""
        <h2>Database Debug Info</h2>
        <p><strong>Database URI:</strong> {app.config['SQLALCHEMY_DATABASE_URI']}</p>
        <p><strong>Connection:</strong> ✅ Success</p>
        
        <h3>Counts:</h3>
        <ul>
            <li>Users: {user_count}</li>
            <li>Projects: {project_count}</li>
            <li>Contributions: {contribution_count}</li>
            <li>Categories: {category_count}</li>
        </ul>
        
        <h3>All Users:</h3>
        <ul>{''.join([f'<li>{user}</li>' for user in user_list])}</ul>
        
        <h3>All Contributions:</h3>
        <ul>{''.join([f'<li>{contrib}</li>' for contrib in contrib_list])}</ul>
        """
        
    except Exception as e:
        return f"<h2>Database Error:</h2><p>{str(e)}</p>", 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_data()
    
    app.run(debug=True)