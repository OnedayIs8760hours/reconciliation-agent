# Docker 部署说明

本文档用于在 Linux 服务器上通过 Docker Compose 部署当前项目，并用 nginx 做反向代理。

## 1. 服务器准备

安装 Docker 和 Docker Compose v2：

```bash
docker --version
docker compose version
```

把项目代码放到服务器，例如：

```bash
cd /opt
git clone <your-repo-url> reconciliation-agent
cd /opt/reconciliation-agent
```

## 2. 配置环境变量

复制部署环境变量模板：

```bash
cp docker/.env.example docker/.env
```

编辑 `docker/.env`：

```bash
nano docker/.env
```

至少需要设置：

```env
WEB_PORT=8080
VITE_API_BASE_URL=
PREVIEW_LLM_PROVIDER=deepseek
MAPPING_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的 DeepSeek API Key
```

说明：

- `VITE_API_BASE_URL` 在 Docker 生产部署中保持为空，前端会请求同源 `/api/...`。
- `PREVIEW_LLM_PROVIDER` 控制 A 表预览分析使用的模型提供商。
- `MAPPING_LLM_PROVIDER` 控制商品映射使用的模型提供商。
- 如果你要使用本机或内网 Ollama，把 `PREVIEW_LLM_PROVIDER=ollama`，并设置 `PREVIEW_LLM_BASE_URL=http://host.docker.internal:11434` 或服务器内网地址。

## 3. 构建并启动

在项目根目录执行：

```bash
docker compose --env-file docker/.env -f docker/docker-compose.yml up -d --build
```

查看容器状态：

```bash
docker compose --env-file docker/.env -f docker/docker-compose.yml ps
```

查看日志：

```bash
docker compose --env-file docker/.env -f docker/docker-compose.yml logs -f backend
docker compose --env-file docker/.env -f docker/docker-compose.yml logs -f frontend
```

本机验证：

```bash
curl http://127.0.0.1:8080/health
```

如果返回 `{"status":"ok"}`，说明前端 nginx 已经能反代到后端。

## 4. 配置宿主机 nginx 反代

如果服务器上已有 nginx，把示例配置复制到 nginx 站点目录：

```bash
sudo cp docker/nginx.host.example.conf /etc/nginx/conf.d/reconciliation-agent.conf
```

编辑域名：

```bash
sudo nano /etc/nginx/conf.d/reconciliation-agent.conf
```

把：

```nginx
server_name example.com;
```

改成你的域名。默认配置会把外部流量反代到 `http://127.0.0.1:8080`，这个端口需要和 `docker/.env` 中的 `WEB_PORT` 保持一致。

检查并重载 nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 5. HTTPS

如果使用 Certbot：

```bash
sudo certbot --nginx -d your-domain.com
```

生成证书后再次检查：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 6. 更新部署

拉取新代码并重建：

```bash
cd /opt/reconciliation-agent
git pull
docker compose --env-file docker/.env -f docker/docker-compose.yml up -d --build
```

清理旧镜像：

```bash
docker image prune -f
```

## 7. 数据持久化

Compose 已经创建两个 volume：

- `reconciliation_tasks`：保存上传的 A/B 表、任务 metadata、生成的 C 表。
- `reconciliation_outputs`：预留给脚本输出目录。

查看 volume：

```bash
docker volume ls | grep reconciliation
```

停止服务但保留数据：

```bash
docker compose --env-file docker/.env -f docker/docker-compose.yml down
```

停止服务并删除持久化数据：

```bash
docker compose --env-file docker/.env -f docker/docker-compose.yml down -v
```

执行 `down -v` 会删除历史任务文件，生产环境谨慎使用。
