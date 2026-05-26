# TrueCadence 生产 JSON 写入安全规范

目的：避免再次出现 root 写入 `/opt/truecadence/data/*.json` 后，`truecadence` 服务用户无法读写，导致登录/注册/邀请码/会员数据功能崩溃。

## 铁律

生产稳定性高于处理速度。任何会影响登录、账号、邀请码、会员、用户数据、训练数据的 JSON 修改，都不能只追求“改完”。必须完成备份、权限、服务和 HTTP 验证。

## 服务用户

当前线上服务：

```text
systemd service: truecadence
service user: www-data
app dir: /opt/truecadence
data dir: /opt/truecadence/data
```

`/opt/truecadence/data/*.json` 的最终 owner/mode 应为：

```text
owner: www-data:www-data
mode: 660
```

`/opt/truecadence/data/` 目录应允许服务用户写入：

```text
owner: www-data:www-data
mode: 775 或更保守但保证 www-data 可写
```

## 修改前流程

1. 确认服务器身份：必须是 TrueCadence 业务服务器 `truecadence-report`。
2. 确认服务用户：

```bash
systemctl show truecadence -p User --value
```

3. 备份目标 JSON：

```bash
cd /opt/truecadence
TS=$(date +%Y%m%d_%H%M%S)
sudo mkdir -p data/backups
sudo cp -a data/users.json data/backups/users.json.before_change_$TS
```

## 修改方式

优先用服务用户写入：

```bash
cd /opt/truecadence
sudo -u www-data python3 your_safe_mutation_script.py
```

如果必须用 root/sudo 写入，写完必须恢复权限：

```bash
sudo chown www-data:www-data /opt/truecadence/data/*.json
sudo chmod 660 /opt/truecadence/data/*.json
```

## 修改后必须检查

运行仓库脚本：

```bash
cd /opt/truecadence
bash scripts/check_data_permissions.sh /opt/truecadence
```

如果服务器没有脚本，可以手动检查：

```bash
cd /opt/truecadence
stat -c '%U:%G %a %n' data data/*.json
sudo -u www-data test -r data/users.json
sudo -u www-data test -w data/users.json
sudo -u www-data python3 -m json.tool data/users.json >/dev/null
```

然后检查服务和页面：

```bash
sudo systemctl restart truecadence
systemctl is-active truecadence
curl -sS -o /dev/null -w 'local=%{http_code}\n' http://127.0.0.1:8502/
sudo journalctl -u truecadence --since '5 min ago' --no-pager -p warning..alert
```

外网也要做一次冒烟：

```bash
curl -k -sS -o /dev/null -w 'https=%{http_code}\n' https://truecadence.cn
```

## 高风险文件

特别注意这些文件：

```text
/opt/truecadence/data/users.json
/opt/truecadence/data/activation_codes.json
/opt/truecadence/data/invitation_codes.json
/opt/truecadence/data/login_sessions.json
/opt/truecadence/data/sessions.json
```

## 完成定义

只有同时满足以下条件，才可以对用户说“完成”：

- 有备份或说明无需备份；
- JSON 语法检查通过；
- owner/mode 正确；
- `www-data` 可读可写；
- `truecadence` 服务 active；
- 本地 `127.0.0.1:8502` 返回 200；
- 外网 HTTPS 返回 200；
- 最近 warning/error 日志无异常。
