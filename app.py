import anonstream

app = anonstream.create_app()

if __name__ == '__main__':
    app.run(port=5051, debug=True)
