# My Agent Skills

个人 agent skills 仓库，用来沉淀可复用的工作流。

## Skills

| Skill | 说明 |
| --- | --- |

## Codex 安装

```bash
./scripts/install-skills.sh
```

安装后重启 Codex，让 skill 索引刷新。

## 开发约定

每个 skill 放在 `skills/<skill-name>/`，并且必须包含 `SKILL.md`。

- `SKILL.md`：触发条件、核心流程、资源导航
- `references/`：较长的规则、模板说明、领域知识
- `scripts/`：需要稳定复用的脚本
- `assets/`：会被复制到产物中的模板和素材
