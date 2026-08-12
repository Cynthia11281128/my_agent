# 通过本地 VPN SOCKS 隧道访问远程服务器上的网站

## 任务描述

配置一台远程 Linux 服务器，让支持代理的命令行工具和脚本能够借用本地电脑已经连接好的 VPN 访问网站。该远程服务器是受限容器 (例如 AutoDL)，缺少虚拟网卡设备和网络管理权限，因此不能在容器内运行完整的系统级 VPN。

## 工作流总结

1. 使用 SSH 连接远程服务器：

   ```bash
   ssh <server-alias>
   ```

2. 检查远程服务器是否支持完整的系统级 VPN 客户端：

   ```bash
   uname -a
   cat /etc/os-release
   ls -l /dev/net/tun 2>/dev/null || echo 'no /dev/net/tun'
   capsh --print | grep -E 'Current:|cap_net_admin'
   ```

   Cisco Secure Client 或 OpenConnect 的完整路由 VPN 需要 TUN 设备和网络管理权限。如果 `/dev/net/tun` 不存在，并且能力集中没有 `cap_net_admin`，应使用代理方案，而不是继续尝试在容器内安装完整 VPN。

3. 在远程服务器上安装最小命令行网络和 VPN/代理工具：

   ```bash
   apt-get update
   DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates openconnect ocproxy iproute2
   ```

4. 验证远程服务器能访问 Oxford VPN 入口：

   ```bash
   curl -I --connect-timeout 15 https://vpn.ox.ac.uk/
   timeout 25s openconnect --authenticate vpn.ox.ac.uk </dev/null
   ```

   如果能够进入 SSO 用户名/密码提示，说明 VPN 入口可达。但这并不能解决容器无法建立完整 VPN 路由的限制。

5. 在本地电脑上，使用官方 Cisco Secure Client 或其他被允许的本地 VPN 客户端连接 Oxford VPN。

6. 从本地电脑打开一个到远程服务器的 SSH 反向动态 SOCKS 隧道：

   ```bash
   ssh -N -R 127.0.0.1:11080 <server-alias>
   ```

   保持这个终端不要关闭。远程服务器会获得一个只监听本机的 SOCKS 代理 `127.0.0.1:11080`；发往该代理的流量会从本地电脑出去，并使用本地电脑当前的 VPN 路由。

7. 在另一个远程服务器 SSH 会话中，确认反向 SOCKS 代理正在监听：

   ```bash
   ss -ltnp | grep 11080
   ```

8. 在当前远程 shell 中配置代理环境变量：

   ```bash
   export ALL_PROXY=socks5h://127.0.0.1:11080
   export HTTPS_PROXY=socks5h://127.0.0.1:11080
   export HTTP_PROXY=socks5h://127.0.0.1:11080
   ```

9. 从远程服务器通过本地电脑的 VPN SOCKS 隧道访问网站：

   ```bash
   curl --socks5-hostname 127.0.0.1:11080 -I https://www.ox.ac.uk/
   curl -L https://<target-url>
   ```

10. 如果使用 Python `requests`，可按需显式配置 SOCKS 代理：

    ```python
    import requests

    proxies = {
        "http": "socks5h://127.0.0.1:11080",
        "https": "socks5h://127.0.0.1:11080",
    }

    response = requests.get("https://<target-url>", proxies=proxies)
    print(response.text[:500])
    ```

    如果缺少 SOCKS 支持，在对应 Python 环境中安装：

    ```bash
    pip install "requests[socks]"
    ```

## 验证

- 确认远程服务器是 Ubuntu 22.04。
- 确认 `/dev/net/tun` 不存在。
- 确认远程容器能力集中没有 `cap_net_admin`。
- 确认 `openconnect` 已安装且可用。
- 确认 `vpn.ox.ac.uk` 可达，并且 OpenConnect 认证探测能进入 Oxford SSO 登录提示。
- 确认远程 `127.0.0.1:11080` 上有反向 SOCKS 代理监听。
- 确认 `curl --socks5-hostname 127.0.0.1:11080 -I https://www.ox.ac.uk/` 返回 HTTP 响应，说明 SOCKS 隧道路径可用。

## 本次运行的特定设置

- 本次使用的远程服务器别名：`seeta`。
- 本次使用的 SOCKS 代理端口：`11080`。
- 远程代理绑定地址：`127.0.0.1`，因此只允许远程服务器本机访问，不对公网暴露。
- 本地电脑需要在打开 SSH 反向隧道前和隧道运行期间保持 Oxford VPN 已连接。
- 代理环境变量只对当前远程 shell 会话生效。新 shell 中需要重新导出，除非写入 shell 启动文件。

## 最终状态

- 远程服务器已安装命令行 VPN/代理相关工具。
- 已建立可用的反向 SOCKS 代理模式，让远程服务器中支持代理的流量可以通过本地电脑当前的 Oxford VPN 出口访问网络。
- 没有在远程服务器上配置完整系统级 VPN，因为该容器缺少所需内核设备和权限。

## 失败尝试 / 备注

- 没有将直接安装或使用 Cisco Secure Client 作为最终方案，因为完整 VPN 客户端需要 TUN 和网络管理权限。
- 由于同样的原因，OpenConnect 的完整路由模式在该远程容器中不可行。
- 早前对 `vpn.medsci.ox.ac.uk` 的探测出现证书链验证问题，而 `vpn.ox.ac.uk` 可以正常进入 SSO 登录流程。
