# TrueCadence Ubuntu 内测部署清单

## 推荐服务器
- Ubuntu 22.04 LTS
- 2核 / 4GB / 40GB+ SSD
- 开放端口：22, 80, 443

## 域名
- 主站：`truecadence.cn`
- www：`www.truecadence.cn`
- 短域：`tcfit.cn` 可跳转到主站

DNS 示例：
```text
truecadence.cn      A     <服务器公网IP>
www.truecadence.cn  CNAME truecadence.cn
候选：tcfit.cn       A     <服务器公网IP>
```

## 上传目录建议
```bash
/opt/truecadence
├── app.py
├── auth.py
├── requirements.txt
├── assets/
├── nutrition_database/
├── data/
└── tmp_uploads/
```

## 服务器初始化
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx certbot python3-certbot-nginx unzip
sudo mkdir -p /opt/truecadence
sudo chown -R $USER:$USER /opt/truecadence
```

## Python 环境
```bash
cd /opt/truecadence
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p data tmp_uploads assets nutrition_database
```

## 运行测试
```bash
cd /opt/truecadence
TRUECADENCE_DEPLOY_MODE=server \
TRUECADENCE_DATA_DIR=/opt/truecadence/data \
TRUECADENCE_TMP_DIR=/opt/truecadence/tmp_uploads \
TRUECADENCE_ASSET_DIR=/opt/truecadence/assets \
TRUECADENCE_SUPPLEMENT_DB=/opt/truecadence/nutrition_database/supplement_db.json \
.venv/bin/python -m streamlit run app.py --server.port 8502 --server.headless true --server.fileWatcherType none
```

## systemd 服务
创建：
```bash
sudo nano /etc/systemd/system/truecadence.service
```

内容：
```ini
[Unit]
Description=TrueCadence Streamlit App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/truecadence
Environment=TRUECADENCE_DEPLOY_MODE=server
Environment=TRUECADENCE_DATA_DIR=/opt/truecadence/data
Environment=TRUECADENCE_TMP_DIR=/opt/truecadence/tmp_uploads
Environment=TRUECADENCE_ASSET_DIR=/opt/truecadence/assets
Environment=TRUECADENCE_SUPPLEMENT_DB=/opt/truecadence/nutrition_database/supplement_db.json
ExecStart=/opt/truecadence/.venv/bin/python -m streamlit run /opt/truecadence/app.py --server.port 8502 --server.address 127.0.0.1 --server.headless true --server.fileWatcherType none
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

权限和启动：
```bash
sudo chown -R www-data:www-data /opt/truecadence/data /opt/truecadence/tmp_uploads
sudo systemctl daemon-reload
sudo systemctl enable --now truecadence
sudo systemctl status truecadence
```

## Nginx 反代
```bash
sudo nano /etc/nginx/sites-available/truecadence
```

内容：
```nginx
server {
    listen 80;
    server_name truecadence.cn www.truecadence.cn tcfit.cn www.tcfit.cn;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8502;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

启用：
```bash
sudo ln -s /etc/nginx/sites-available/truecadence /etc/nginx/sites-enabled/truecadence
sudo nginx -t
sudo systemctl reload nginx
```

## HTTPS
```bash
sudo certbot --nginx -d truecadence.cn -d www.truecadence.cn
```

短域可后续单独加：
```bash
sudo certbot --nginx -d tcfit.cn -d www.tcfit.cn
```

## 重要差异
- 本地版 ZWO：写入本机 `Documents/Zwift/Workouts/TrueCadence`。
- 服务器版 ZWO：`TRUECADENCE_DEPLOY_MODE=server` 时生成 ZIP 下载。
- 数据目录必须持久化并备份：`/opt/truecadence/data`。

## 冒烟测试
1. 访问 `http://服务器IP` 或域名。
2. 注册/登录。
3. 填骑手档案。
4. 上传 FIT。
5. 查看功率仪表盘。
6. 填训练反馈。
7. 生成训练课表。
8. 下载 ZWO ZIP。
9. 查看恢复/营养/目标页。

## 备份
```bash
sudo tar -czf /opt/truecadence-backup-$(date +%F).tar.gz /opt/truecadence/data
```
