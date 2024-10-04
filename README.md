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


# Documentação Front-End Sistema de diárias e passagens FESF-SUS

# \*\*Visão Geral:\*\*

\*\*Nome do Projeto: Sistema de diárias e passagens FESF-SUS\*\*

Este é o repositório do **Front-end** do sistema de diárias e passagens FESF-SUS.Este front-end é a parte visual de uma aplicação que intenciona facilitar o registro e calculo de diárias dentro das dinâmicas institucionais da FESF-SUS.

Este projeto está sendo construído sobre a infraestrutura sólida do **Next.js**, um framework **React** altamente performático. Ele incorpora uma variedade de bibliotecas e ferramentas essenciais para criar uma experiência de usuário moderna e responsiva. A integração do **FontAwesome** proporciona ícones escaláveis e estilizados, enquanto o Swiper adiciona funcionalidades de carrossel dinâmico. A combinação do **ESLint** e **Prettier** assegura a consistência e qualidade do código, com verificações automáticas durante o estágio de pré-commit, graças ao **Husky**.

O projeto adota a abordagem componentizada do **React**, promovendo a reutilização eficiente de código e facilitando a manutenção. O ambiente de desenvolvimento é simplificado pelo script **"dev"**, que inicia um servidor local para testes contínuos. O processo de construção é gerenciado pelo script **"build"**, que compila o código para produção, enquanto o script **"start"** inicia um servidor de produção otimizado. O uso de tecnologias como **Tailwind CSS**, contribuem para a riqueza da interface e aprimoram a usabilidade.

Este projeto prevê a integração com uma backend contruido em **Python**, utilizando **Fast API** como framework backend. O **Backend** é responsável por receber o e-mail do usuário e retornar um link de acesso a um formulário para registro e cálculo de diárias e passagens da **FESF-SUS**. O formulário é a tela principal da aplicação e é responsável por colher as informações do usuário e enviá-las ao **backend** para que processe os dados e retorne os resultados esperados.

### **Versão**

**0.1.0**

### **Configuração de Controle de Versão**

O projeto é configurado como privado (**`private: true`**) e utiliza o Husky para definir ganchos (hooks) no Git. Atualmente, o único gancho configurado é o **`pre-commit`**, que executa o **`lint-staged`** antes de cada commit.

```jsx
"husky": {
"hooks": {
"pre-commit": "lint-staged"
}
}
```

O **`lint-staged`** é configurado para executar o ESLint automaticamente em arquivos JavaScript e JSX no diretório **`src`** antes de cada commit.

```jsx
"lint-staged": {
"src/**/*.{js, jsx}": [
"npm run lint --fix"
]
}
```

### **Scripts**

O projeto possui os seguintes scripts configurados:

- **dev**: Inicia o servidor de desenvolvimento do Next.js.
- **build**: Compila o projeto para produção.
- **start**: Inicia o servidor de produção do Next.js.
- **lint**: Executa o ESLint para verificar e corrigir problemas de código.
- **prepare**: Instala o Husky durante a configuração do projeto.

```jsx
"scripts": {
"dev": "next dev",
"build": "next build",
"start": "next start",
"lint": "next lint",
"prepare": "husky install"
}
```

## **Dependências**

### **Pacotes Principais**

1. **@chakra-ui/react** (v2.7.1)
2. **@emotion/react** (v11.11.1)
3. **@emotion/styled** (v11.11.0)
4. **@fortawesome/fontawesome-svg-core** (v6.4.0)
5. **@fortawesome/free-brands-svg-icons** (v6.4.0)
6. **@fortawesome/free-regular-svg-icons** (v6.4.0)
7. **@fortawesome/free-solid-svg-icons** (v6.4.0)
8. **@fortawesome/react-fontawesome** (v0.2.0)
9. **autoprefixer** (v10.4.14)
10. **eslint-config-next** (v13.4.4)
11. **file-loader** (v6.2.0)
12. **framer-motion** (v10.12.18)
13. **lint-staged** (v13.2.2)
14. **next** (v13.4.4)
15. **postcss** (v8.4.24)
16. **react** (v18.2.0)
17. **react-burger-menu** (v3.0.9)
18. **react-dom** (v18.2.0)
19. **react-pdf** (v7.1.2)
20. **react-pro-sidebar** (v1.1.0-alpha.1)
21. **swiper** (v9.4.1)
22. **tailwindcss** (v3.3.2)

### **Dependências de Desenvolvimento**

1. **eslint** (v8.41.0)
2. **eslint-config-prettier** (v8.8.0)
3. **eslint-plugin-prettier** (v4.2.1)
4. **eslint-plugin-react** (v7.32.2)
5. **eslint-plugin-react-hooks** (v4.6.0)
6. **husky** (v8.0.0)
7. **prettier** (v2.8.8)

## **Instalação**

1. Clone o repositório do projeto.

```jsx
git clone <URL_DO_REPOSITORIO>
cd novo_site
```

1. Instale as dependências.

```jsx
npm install
```

## **Uso**

### **Desenvolvimento**

Para iniciar o servidor de desenvolvimento do Next.js, utilize o seguinte comando:

```jsx
npm run dev
```

### **Produção**

Para compilar o projeto para produção, execute:

```jsx
npm run build
```

Em seguida, inicie o servidor de produção:

```jsx
npm start
```

### **Linting**

Para verificar e corrigir problemas de código usando o ESLint, utilize o comando:

```jsx
npm run lint
```

## **Contribuição**

1. Faça um fork do projeto.
2. Crie uma branch para a sua feature (**`git checkout -b feature/NomeDaFeature`**).
3. Faça commit das suas alterações (**`git commit -am 'Adiciona NovaFeature'`**).
4. Faça push para a branch (**`git push origin feature/NomeDaFeature`**).
5. Abra um Pull Request.
