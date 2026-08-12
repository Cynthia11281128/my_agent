# SSH 的 VPN 分流路由

## 设置 / 输入

这个流程用于在 Windows 上配置路由，让指定 SSH 服务器绕过全局 VPN，同时其他流量继续按需使用 VPN。

- VPN 客户端：`<vpn-client>`
- SSH 别名：`<server-alias>`
- SSH 主机：`<server-host>`
- SSH 端口：`<ssh-port>`
- SSH 用户：`<ssh-user>`
- 本地非 VPN 网关：`<local-gateway>`
- 本地非 VPN 网卡：`<local-interface>`
- 当前解析到的服务器 IP：`<server-ip>`

修改路由需要使用管理员 PowerShell。

## 任务描述

在保持 VPN 连接以满足部分工具联网需求的同时，让连接远程服务器的 SSH 流量走本地网络接口，从而改善 VS Code Remote SSH、终端、远程文件浏览和图片预览的速度。

## Workflow Summary

1. 检查 SSH 配置，确认实际生效的主机和端口：

   ```bash
   ssh -G <server-alias> | rg "^(hostname|user|port|identityfile) "
   ```

2. 在管理员 PowerShell 中把 SSH 主机解析为当前 IPv4 地址：

   ```powershell
   $hostName = "<server-host>"
   $ip = (Resolve-DnsName $hostName -Type A | Where-Object { $_.IPAddress } | Select-Object -First 1 -ExpandProperty IPAddress)
   $ip
   ```

3. 选择当前启用的本地网络接口，排除 VPN 网卡：

   ```powershell
   $gw = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" -and $_.InterfaceAlias -notmatch "Cisco|AnyConnect|VPN" } | Select-Object -First 1
   $gw.InterfaceAlias
   $gw.IPv4DefaultGateway.NextHop
   ```

4. 给解析出的服务器 IP 添加一条通过本地网关的主机路由：

   ```powershell
   New-NetRoute -DestinationPrefix "$ip/32" -InterfaceIndex $gw.InterfaceIndex -NextHop $gw.IPv4DefaultGateway.NextHop -RouteMetric 1
   ```

5. 验证 TCP 连通性和实际选路：

   ```powershell
   Test-NetConnection $ip -Port <ssh-port> -InformationLevel Detailed
   ```

6. 使用 SSH 或 VS Code Remote SSH 连接，可以使用域名，也可以使用固定 IP：

   ```powershell
   ssh -p <ssh-port> <ssh-user>@<server-ip>
   ```

7. 如果希望 VS Code 行为更稳定，可以把 SSH 配置固定到解析出的 IP：

   ```sshconfig
   Host <server-alias>
     HostName <server-ip>
     User <ssh-user>
     Port <ssh-port>
     IdentityFile <identity-file>
   ```

8. 如果要恢复为默认路由，让该服务器重新按系统默认路径走，删除静态主机路由：

   ```powershell
   Remove-NetRoute -DestinationPrefix "<server-ip>/32" -Confirm:$false
   ```

   如有需要，可以分别删除两个路由存储中的记录：

   ```powershell
   Remove-NetRoute -DestinationPrefix "<server-ip>/32" -PolicyStore ActiveStore -Confirm:$false
   Remove-NetRoute -DestinationPrefix "<server-ip>/32" -PolicyStore PersistentStore -Confirm:$false
   ```

## Verification

- `Test-NetConnection` 对 SSH IP 和端口测试成功。
- 实际选中的接口是本地以太网接口。
- 实际选中的下一跳是本地网关。
- 结果确认 SSH 路由走的是非 VPN 路径。
- `tracert` 没有作为最终验证依据，因为 ICMP 超时并不代表 TCP/SSH 不通。

## Final State

- 已存在一条 `<server-ip>/32` 通过 `<local-gateway>` 的静态主机路由。
- 指向 `<server-ip>:<ssh-port>` 的 SSH 和 VS Code Remote SSH 流量应走本地网络接口。
- 其他需要 VPN 的工具仍可继续通过 VPN 访问对应目标。

## Failed Attempts / Notes

- 复制很长的 PowerShell 命令时，如果换行拆开了命令名或参数，会导致解析错误。逐行执行更可靠。
- `Resolve-DnsName` 可能先返回没有 `IPAddress` 属性的记录，因此需要用 `Where-Object { $_.IPAddress }` 过滤。
- 如果 SSH 主机以后解析到新的 IP，需要为新 IP 重新添加路由，或者更新固定 IP 的 SSH 配置。
- 如果 VPN 客户端强制执行严格的全隧道策略，本地分流路由可能会被 VPN 策略阻止。

## 占位符实际值

- `<vpn-client>`：Cisco AnyConnect
- `<server-alias>`：seeta
- `<server-host>`：connect.bjb2.seetacloud.com
- `<ssh-port>`：52496
- `<ssh-user>`：root
- `<local-gateway>`：10.10.64.1
- `<local-interface>`：显示为 `以太网` 的以太网接口
- `<server-ip>`：106.38.204.136
- `<identity-file>`：该 SSH 别名配置使用的身份密钥文件
