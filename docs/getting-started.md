## 1 Dependencies

To get these docs running you have already installed python deps with Poetry. Nice!. Now the only thing left to do is to install JS deps. For that I like to use `pnpm`. So run this command:

```
pnpm i
```

To get things going, let's try starting the deb frontend server. This will start the css and js complilation and will create a build folder.

```
pnpm run start
```

## 2 Prepare the files

- Change the `.env.example` file name to `.env`.


## 3 Creating the Database

The next thing you want to do is to create and apply the migrations. First run:

```
poetry run python manage.py makemigrations
```

then

```
poetry run python manage.py migrate
```

This will create a SQLite database with all the necessary tables.

## 4 Start the dev server

Start by building the frontend resource. You can do that by running:

```
npm run start
```

You should see something like this:

```
webpack 5.73.0 compiled successfully in 3254 ms
```

Note:
Make sure you are running tht latest LTS Node. As of this writing it is 16. You can activate it with `nvm use 16` if you have nvm installed.

Now let's start the python server by `poetry run python manage.py runserver` in a new terminal window (we don't want to close the npm stuff. You can do that by pressing Ctrl+N while in VS Code Terminal). If you need a primer on how to use poetry, check out [this blog post](https://builtwithdjango.com/blog/basic-django-setup)

---

Et Voila, you should have a basic site running.
