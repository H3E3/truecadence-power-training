from pathlib import Path
p = Path('/etc/nginx/sites-available/truecadence')
s = p.read_text()
if 'location /static/' not in s:
    needle = '    location /auth-bridge/ {\n'
    block = '''    location /static/ {
        alias /opt/truecadence/static/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }

'''
    s = s.replace(needle, block + needle)
    p.write_text(s)
