#SQLITE3 SQLALCHEMY FASTAPI DATABASE SERVER!!
#SAME SCHEMA DESIGN IN SCHEMA.SQL FILE JUST WRITTEN USING SQLALCHEMY!!
#WITH SQLALCHEMY, IT HANDLES SQL QUERIES MEANING YOU DON'T HAVE TO WRITE SQL SYNTAX

#SQLALCHEMY IS THE MOST POPULAR ORM FOR PYTHON. WHAT'S AN ORM? OBJECT RELATIONAL MODEL??
#SQLALCHEMY ENABLES PORTABILITY SUCH THAT CHANGING A DMBS FROM SQLITE TO POSTGRES OR MYSQL, YOU JUST CHANGE THE CONFIGURATION LINE ONLY.
#THE ARCHITECTURE HAS THREE LAYERS. SQLALCHEMY MODEL CLASSES DEFINE WHAT WE ARE GOING TO STORE TO THE DATABASE,
#PYDANTIC MODELS DEFINE THE API CONTRACT OF HOW WE CAN RECEIVE REQUESTS AND SEND BACK RESPONSES.
#THEN WE HAVE THE API ENDPOINT ROUTES THAT HANDLE THE REQUESTS.
#HAVING SEPARATE SQLALCHEMY AND PYDANTIC MODELS GIVES US GREATER CONTROL SUCH THAT YOU CAN CHANGE ONE WITHOUT AFFECTING THE OTHER
#AND YOU ALSO GET TO UNDERSTAND WHAT'S HAPPENING IN YOUR APP. THERE IS A CONCEPT CALLED SQLMODELS WHICH TRYING TO COMBINE THESE TWO MODELS INTO ONE.
#THE DATA FLOW NOW BECOMES, PYDANTIC MODELS DEFINE AND VALIDATE OUR API REQUESTS CONTRACT, SQLALCHEMY MODELS PERSIST AND RETRIEVES DATA, PYDANTIC FORMATS THE RESPONSE,
#AND THE RESPONSE GOES OUT. HENCE WE HAVE CLEAR BOUNDARIES BETWEEN EACH LAYER.
#SQLITE IS GREAT FOR LEARNING AND DEVELOPMENT, BUT NOW IN PRODUCTION, YOU NEED POSTGRES OR MYSQL AND WITH SQLALCHEMY, YOU CHANGE DATABASES AND THE ONLY THING 
#THAT NEEDS TO CHANGE IS THE DATABASE URL.

#create_engine() creates a connection to the database. we set check_same_thread to False because SQLITE allows operations from the same thread but FASTAPI handles
#requests from multiple threads.
#You pass the SQLALCHEMY_DATABASE_URL to create_engine as the first argument, second argument is connect_args is a dictionary which sets check_same_thread to False.
#We also need SessionLocal which is a factory that creates database sessions. A session is a transaction with the database. Each request gets it's own session.
#We call session_maker() and return it's output to SessionLocal. We set autocommit and autoflush to False since we want to control when commits happen. Third argument
#to session_maker() is bind which is set to engine. Research what all these mean.
#get_db() is a dependency function that provides sessions to our routes. You use the with statement so that the session acts as a context manager, kinda like opening
#a file which now offers clean up like closing the session even if an error occurs.
#FastAPI's dependency injection calls get_db for each request and handles the cleanup automatically.
#RESEARCH MORE ABOUT DEPENDENCY INJECTION.
#DEPENDENCY INJECTION: This is basically a way of saying, hey this routes needs a database session to work, so go ahead and give it one.
#Instead of creating a session inside the route, we declare that we need one and FastAPI just provides it.

#Next we want to define our database models inside models.py and this will define our database tables using SQLALCHEMY ORM
#We need imports from sqlalchemy such as DateTime, ForeignKey, Integer, String, Text which are column types and ForeignKey is under relationships.
#We also import from sqlalchemy.orm Mapped and mapped_colum and relationship. We also import Base from database.
#Now for each entity, we create a class with that entity name which inherits from Base as a parent.
#To set a table name we use the syntax __tablename__ equal to the name of the table.
#To define the columns, we use Mapped(int) which is just a type hint declaration for our column name and then we use mapped_column() to define the column with
#the individual properties such as contraints for the column. Arguments to mapped_column include fields like Integer which was imported from sqlalchemy as column type
#and this defines our column type as an integer, primary_key=True which autoincrements our ids, then index=True. Research what index does.
#Other parameters for mapped_column include unique which makes sure each column entry is unique, then we also have nullable which ensures that the column is required.
#So in regular SQL syntax, unique == UNIQUE, nullable == NOT NULL, primary_key == PRIMARY KEY. These are just the column constraints like in SQL
#Notice what he is doing with the image persistence. He is only storing the filename, like otunga.img and not the image path. This is a production best practise
#because this allows us to decouple our database from our file structure. Meaning that if we were to change our file structure or rename some file names, we don't have
#to change the database, we only change one place. This separates the data from the presentation.
#We imported relationship from sqlalchemy.orm which helps us define relationship between post and author which is a ONE TO MANY relationship. This means that one
#user can have many posts. Notice the syntax posts: Mapped[list[Post]] = relationship(back_populates="author"). We are basically calling relationship like
#a function then research what the parameter back_populates does.
#You will notice that we are referencing the class Post, in the posts column declaration before actually defining Post. This is called forward referencing and for it
#to work properly, you need to import from __future__ import annotations at the very top of your file as the first import, this is important. It has to be first.
#Now this imports allows forward referencing in older Python versions below Python 3.14. Versions that are Python 3.14 and above, forward referencing works just fine
#without having that import. Research why forward referencing is different from something like NameError situations.

#In our main.py file, we need more imports. We import Depends from FastAPI which is how we achieve dependency injection for our database sessions required for routes.
#From sqlalchemy we import select which is how we do the SQL queries, from sqlalchemy.orm we import Session which will act as a type hint for the database sessions.
#From database.py we import engine, Base which is what we use to create the database tables, and also get_db() which is our dependency inject function for providing
#database sessions.
#The way we create our database table is with this syntax: Base.metadata.create_all(bind=engine). Simple clean one line.
#This looks at all the database models that import from Base and creates the tables if they don't already exist. This is idempotent meaning that the line can run
#multiple lines and the tables will just be created once at app startup.

#Now we need to create endpoints for the user. We need endpoints for creating a user which will take the UserCreate model definition as a parameter as a way to validate
#the data provided when creating a user by Pydantic, so UserCreate is a contract spec for creating user request shape. This create_user() API function will need a 
#database session for it to work and so instead of creating a database session inside the route, we will pass the database session as a parameter to the FastAPI route
#function and FastAPI will handle mechanics for providing a database session. This is how we use dependency injection for sessions.
#We pass the session as a parameter with this syntax. Annotated[Session, Depends(get_db)]. Annotated is how we add metadata to variables/attributes in Python.
#It's mostly for type hints. The first argument to Annotated is Session which is now the type declaration for a database session, then the second argument is Depends.
#This is FastAPI import syntax for how we call get_db. So Depends(get_db) returns a database session before the API route function runs and this returned session is
#what is set as the db parameter. We will pass this Annotated[Session, Depends(get_db)] parameter to all our API routes functions.

#Now I am not writing notes for the course domain syntax issues like how to create a new user, but see how the sql query is written.
#Before creating a new user, we need to check whether the user already exists and so we need to query the users database table to check if we have a user that matches.
#Check out the syntax: result = db.execute(select(models.User).where(models.User.username == user.username))
#This is basically Python since there is no raw SQL syntax being manually written. SQLALCHEMY handles all that and this is my main attraction towards SQLALCHEMY.
#Then we do existing_user = result.scalars().first(). According to course instructor, this gets the first user object in the response or None. Check syntax meaning.