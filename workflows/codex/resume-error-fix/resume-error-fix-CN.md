# Codex Resume Error Fix

## 设置 / 输入

这个流程适用于 Codex resume 失败，并提示目标 thread 已经有 active writer 的情况。

输入：

- `<codex-session-jsonl>`：resume 报错中显示的 session JSONL 文件。
- `<stale-codex-pids>`：仍然打开该 session 文件的 Codex 进程 ID。

需要的工具：

- `lsof`
- `ps`
- `kill`

## 任务描述

修复由旧 Codex 进程继续持有 session JSONL 写入权导致的 Codex TUI resume 失败，同时不删除也不修改 session 文件。

## 流程总结

1. 从 resume 报错中复制 session JSONL 路径。
2. 检查哪个进程仍然打开着该 session 文件：

   ```bash
   lsof <codex-session-jsonl>
   ```

3. 从 `lsof` 输出中确定相关的 Codex 进程 ID。
4. 检查这些进程及其父进程、终端关系：

   ```bash
   ps -o pid,ppid,tty,stat,lstart,cmd -p <stale-codex-pids>
   ```

5. 确认这些进程是 failed resume 目标对应的旧 Codex/TUI 进程组，而不是当前正在使用的会话。
6. 只对旧 writer 进程发送正常终止信号：

   ```bash
   kill -TERM <stale-codex-pids>
   ```

7. 稍等片刻，然后确认这些进程已经退出：

   ```bash
   ps -o pid,ppid,tty,stat,lstart,cmd -p <stale-codex-pids>
   ```

8. 确认 session 文件已经不再被进程占用：

   ```bash
   lsof <codex-session-jsonl>
   ```

9. 重新执行 Codex resume。

## 验证

- 初次运行 `lsof <codex-session-jsonl>` 时，能看到 Codex 进程正在占用 session 文件。
- `ps -o pid,ppid,tty,stat,lstart,cmd -p <stale-codex-pids>` 确认该占用者属于旧 Codex/TUI 进程组。
- 执行 `kill -TERM <stale-codex-pids>` 后，`ps` 不再列出这些进程。
- 最后一次运行 `lsof <codex-session-jsonl>` 时，没有任何占用者输出。

## 最终状态

- 旧 Codex writer 已停止。
- session JSONL 文件仍保留原位，未被删除或编辑。
- active-writer 冲突已清除，因此可以再次 resume 该 session。

## 失败尝试 / 备注

- 不要通过删除 session JSONL 文件来修复这个问题。
- 优先使用 `kill -TERM`。只有旧进程无法退出时，才考虑更强的信号。
- 系统上可能同时运行多个 Codex 进程；结束进程前必须先确认真正占用目标文件的是哪一个。

## 占位符实际值

- `<codex-session-jsonl>`：resume 报错中的 Codex session JSONL 路径，位于用户的 Codex sessions 目录下。
- `<stale-codex-pids>`：`2261371 2261378`
