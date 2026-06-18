import os

template_dir = os.path.join(os.path.dirname(__file__), "portal", "templates")

old_path = os.path.join(template_dir, "loja.html")
new_path = os.path.join(template_dir, "loja_nova.html")

old = open(old_path, "r", encoding="utf-8").read()

# Insert LOJA NOVA ATIVA banner after <body>
old = old.replace(
    "<body>",
    '<body>\n<div style="background:yellow;color:red;font-size:24px;font-weight:700;text-align:center;padding:8px;border-bottom:2px solid red">LOJA NOVA ATIVA</div>',
    1,
)

open(new_path, "w", encoding="utf-8").write(old)
print(f"Created {new_path}")
print(f"Size: {len(old)} bytes")
print("LOJA NOVA ATIVA banner added")

# Verify banner present
verify = open(new_path, "r", encoding="utf-8").read()
if "LOJA NOVA ATIVA" in verify:
    print("OK: Banner found in loja_nova.html")
else:
    print("ERROR: Banner NOT found")
