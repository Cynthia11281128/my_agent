# My Agent Skills

个人 agent skills 仓库，用来沉淀可复用的工作流。

## 公开 Skills

| Skill | 说明 |
| --- | --- |
| `connect-folder-to-github` | 将本地文件夹连接到远程 GitHub 仓库。 |
| `connect-github-account` | 为本机设置并验证 GitHub SSH 访问。 |
| `local-skill-creator` | 使用 upstream Skill Creator 工作流创建项目本地 Codex skills。 |
| `local-skill-setup` | 设置项目本地 Codex skills 和按文件夹生效的 skill 范围。 |
| `md-translate-inplace-eng` | 在原 Markdown 文件内将中文翻译成英文，并轻量修正已有英文语法。 |
| `md-translate-pair-cn` | 将英文 Markdown 翻译成同目录下的中文 `-CN.md` 文件。 |
| `push-safety-check` | push 前扫描 repo 中不应推送的私密信息。 |
| `setup-collaborator` | 澄清并协作处理非代码类设置和配置任务。 |
| `summarize-workflow` | 生成中英文成对的可复用工作流总结。 |
| `md-sync-bilingual` | 基于显式变更标记同步中英文 Markdown 文件。 |
| `md-edit` | 编辑英文 Markdown，并标记变更以同步中文配对文件。 |
| `quick-data-transfer` | 从已配置服务器下载文件或文件夹。 |

## 私有 Skills

| Skill | 说明 |
| --- | --- |
| `audit-skill-index` | 检查 README skill 索引是否与公开和私有 skill 文件夹一致。 |
| `my-skill-creator` | 按 upstream 规则创建 skills，支持 public/private 位置，并同步维护中英文 README 索引。 |

## Codex 安装

```bash
./scripts/install-skills.sh
```

安装后重启 Codex，让 skill 索引刷新。

## 开发约定

公开 skill 放在 `skills/<skill-name>/`。私有 skill 放在 `private/skills/<skill-name>/`。每个 skill 都必须包含 `SKILL.md`。

- `SKILL.md`：触发条件、核心流程、资源导航
- `references/`：较长的规则、模板说明、领域知识
- `scripts/`：需要稳定复用的脚本
- `assets/`：会被复制到产物中的模板和素材
