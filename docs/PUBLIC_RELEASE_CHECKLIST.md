# GitHub 发布前清单

本项目当前仍是本地实验区。初始化 Git 和公开发布前，按下面顺序检查。

## 必须完成

- [ ] 决定仓库名、简介和公开/私有可见性；
- [ ] 选择许可证并添加 `LICENSE`；
- [ ] 检查 `.gitignore` 是否覆盖本地状态、报告、临时渲染物和环境配置；
- [ ] 扫描 Windows 用户目录、开发盘符路径和 Unix 用户目录等个人路径；
- [ ] 把测试夹具中的个人路径替换为 `example` 占位路径；
- [ ] 检查 `archive/` 中模板和参考资料的许可证及公开权限；
- [ ] 在干净目录重新运行结构校验和 smoke tests；
- [ ] 至少用一个真实高教杯项目完成 forward-test；
- [ ] 确认 README 不承诺尚未验证的真实求解、部署或发表能力。

## 建议的 Git 初始流程

这些命令应在项目根目录执行：

```powershell
git init
git add .
git status
git commit -m "Initial local Higher Education Cup skills rebuild"
git branch -M main
git remote add origin <your-github-repository-url>
git push -u origin main
```

首次发布前先执行 `git status`，确认没有个人路径、运行报告、临时文件或未授权模板。

## 许可证选择

许可证是公开发布的法律选择，不由 skill 自动决定。若暂时不确定，先保持私有仓库，不要用没有依据的许可证声明。



