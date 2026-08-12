# Remote Server Access Through a Local VPN SOCKS Tunnel

## Task Description

Configure a remote Linux server so proxy-aware command-line tools and scripts can access websites through a VPN connection that is already active on the user's local computer. The remote server is a restricted container (for example, AutoDL) and cannot run a full system-level VPN because it lacks the required virtual network device and network administration capability.

## Workflow Summary

1. Connect to the remote server with SSH:

   ```bash
   ssh <server-alias>
   ```

2. Check whether the remote server can support a full system-level VPN client:

   ```bash
   uname -a
   cat /etc/os-release
   ls -l /dev/net/tun 2>/dev/null || echo 'no /dev/net/tun'
   capsh --print | grep -E 'Current:|cap_net_admin'
   ```

   A full Cisco Secure Client or OpenConnect routed VPN requires a TUN device and network administration capability. If `/dev/net/tun` is missing and `cap_net_admin` is absent, use a proxy-based workaround instead of trying to install a full routed VPN inside the container.

3. Install minimal command-line networking and VPN/proxy tools on the remote server:

   ```bash
   apt-get update
   DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates openconnect ocproxy iproute2
   ```

4. Verify that the Oxford VPN endpoint is reachable from the remote server:

   ```bash
   curl -I --connect-timeout 15 https://vpn.ox.ac.uk/
   timeout 25s openconnect --authenticate vpn.ox.ac.uk </dev/null
   ```

   Reaching the SSO username/password prompt confirms endpoint reachability. This does not override the container limitation for full VPN routing.

5. On the local computer, connect to the Oxford VPN using the official Cisco Secure Client or another approved local VPN client.

6. From the local computer, open an SSH reverse dynamic SOCKS tunnel to the remote server:

   ```bash
   ssh -N -R 127.0.0.1:11080 <server-alias>
   ```

   Keep this terminal open. The remote server receives a local-only SOCKS proxy at `127.0.0.1:11080`; traffic sent to that proxy exits through the local computer, including the local computer's active VPN routing.

7. In a separate SSH session on the remote server, confirm that the reverse SOCKS proxy is listening:

   ```bash
   ss -ltnp | grep 11080
   ```

8. Configure the current remote shell to use the SOCKS proxy:

   ```bash
   export ALL_PROXY=socks5h://127.0.0.1:11080
   export HTTPS_PROXY=socks5h://127.0.0.1:11080
   export HTTP_PROXY=socks5h://127.0.0.1:11080
   ```

9. Access websites from the remote server through the local computer's VPN-backed SOCKS tunnel:

   ```bash
   curl --socks5-hostname 127.0.0.1:11080 -I https://www.ox.ac.uk/
   curl -L https://<target-url>
   ```

10. For Python `requests`, configure SOCKS proxies explicitly when needed:

    ```python
    import requests

    proxies = {
        "http": "socks5h://127.0.0.1:11080",
        "https": "socks5h://127.0.0.1:11080",
    }

    response = requests.get("https://<target-url>", proxies=proxies)
    print(response.text[:500])
    ```

    If SOCKS support is missing, install it in the relevant Python environment:

    ```bash
    pip install "requests[socks]"
    ```

## Verification

- Confirmed the remote server was Ubuntu 22.04.
- Confirmed `/dev/net/tun` was absent.
- Confirmed `cap_net_admin` was absent from the remote container capability set.
- Confirmed `openconnect` was installed and available.
- Confirmed `vpn.ox.ac.uk` was reachable and produced the Oxford SSO login prompt through OpenConnect authentication probing.
- Confirmed the reverse SOCKS proxy listened on remote `127.0.0.1:11080`.
- Confirmed `curl --socks5-hostname 127.0.0.1:11080 -I https://www.ox.ac.uk/` returned an HTTP response, showing that the SOCKS tunnel path worked.

## Run-Specific Settings

- Remote server alias used in this run: `seeta`.
- SOCKS proxy port used in this run: `11080`.
- Remote proxy bind address: `127.0.0.1`, so it was only accessible from the remote server itself and was not exposed publicly.
- The local computer must keep the Oxford VPN session active before and during the SSH reverse tunnel session.
- Proxy environment variables were only set for the active remote shell session. They must be re-exported in new shells unless added to shell startup files.

## Final State

- The remote server was prepared with command-line VPN/proxy tooling.
- A working reverse SOCKS proxy pattern was established so the remote server can send proxy-aware traffic through the local computer's active Oxford VPN.
- The remote server was not configured with a full system-level VPN because the container lacked the required kernel device and capabilities.

## Failed Attempts / Notes

- Installing or using Cisco Secure Client directly on the remote container was not pursued as the final path because full VPN clients require TUN and network administration privileges.
- Direct full OpenConnect routing was not viable in the remote container for the same reason.
- Earlier probes of `vpn.medsci.ox.ac.uk` showed certificate-chain verification issues, while `vpn.ox.ac.uk` reached the SSO login flow cleanly.
