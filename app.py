import anonstream

if __name__ == '__main__':
    app = anonstream.create_app()
    app.run(port=5051, debug=True)
