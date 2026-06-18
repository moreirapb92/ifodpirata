"""Inicia o Portal Web IfodPirata."""
from portal.app import create_app

if __name__ == "__main__":
    app = create_app()
    print("=" * 50)
    print("  Portal IfodPirata")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
