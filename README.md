# new_suap
### Branches Principais
_____

- **main***: Branch de produção, contém a versão estável do projeto.
- **develop***: Branch de desenvolvimento contínuo, onde novas features são integradas antes de serem movidas para a `main`.

> Cada uma dessas branches deve estar vinculada a ambientes, pipelines e arquivos `.env` separados.

### Branches de Vida Curta
_____

- **Feature/**: Usada para adicionar novas funcionalidades ao projeto.
  - Exemplo: `feature/add-user-authentication`
- **Fix/**: Usada para corrigir bugs e erros específicos.
  - Exemplo: `fix/correct-login-redirect`
- **Refactor/**: Usada para reestruturar o código sem alterar o comportamento externo.
  - Exemplo: `refactor/optimize-api-calls`
- **Bump/**: Usada para atualizar dependências e pacotes.
  - Exemplo: `bump/update-react-version`
- **Release/**: Usada para preparar novas versões e releases do projeto.
  - Exemplo: `release/v1.2.0`

### Organização de Repositórios
_____

- **Repositórios separados para back-end e front-end**: Cada parte do projeto deve ter seu próprio repositório para facilitar o gerenciamento e o controle de versão.

---

## Commits Convencionais
_____

Devemos seguir o padrão de [Conventional Commits](https://www.conventionalcommits.org/) para manter a consistência e a clareza nos históricos de commits. Abaixo estão os tipos de commits que devem ser usados:

- **feat**: Adição de uma nova funcionalidade (feature).
- **fix**: Correção de um bug.
- **refactor**: Modificação no código que não altera a funcionalidade, como refatorações.
- **chore**: Tarefas menores, como atualizações de scripts ou configurações.
- **style**: Alterações de estilo e formatação (espaçamento, ponto e vírgula, etc.), sem mudar a lógica do código.
- **bump**: Atualizações de dependências e pacotes.
- **docs**: Alterações relacionadas à documentação.
- **build**: Alterações que afetam o sistema de build ou dependências externas (ex: gulp, npm).
- **devops**: Alterações relacionadas a DevOps, infraestrutura e scripts de deployment.
- **revert**: Reversão de um commit anterior.

### Exemplo de Commit
_____

```
feat: adiciona funcionalidade de autenticação de usuário
fix: corrige bug no redirecionamento de login
```

---

## Versionamento e Releases
_____
[Semantic Versioning 2.0.0](https://semver.org/)

- **Semantic Versioning**: Usar versionamento semântico para gerenciar as releases (`v1.0.0`, `v1.1.0`, etc.).

- **Tags de Release**: Cada versão estável deve ser marcada com uma tag correspondente no Git (`v1.0.0`, `v1.1.0`, etc.).

- **Semantic Release**: Automatizar a criação de releases com base nos commits, para garantir consistência nas versões.


## Boas Práticas de Pull Requests
_____

- **Sem commits diretos na branch `main`**: Todos os desenvolvimentos devem passar por uma PR (Pull Request) e ser revisados por outro desenvolvedor antes de serem integrados à branch principal.
- **Revisão obrigatória**: Exceto em casos de extrema urgência, todo PR deve ser revisado.
- **Uso de `rebase`**: Prefira usar o método de rebase ao invés de merge para manter o histórico linear e limpo.
