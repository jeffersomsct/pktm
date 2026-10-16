```markdown
# 🐙 Guia Básico do Git: Upload e Resgate de Projetos

Este guia apresenta os comandos essenciais do Git para enviar (upload) um projeto do seu computador para um repositório online (como o GitHub) e para resgatar (baixar) esse projeto em outro computador ou atualizar sua versão local.

---

## ⚙️ 1. Configuração Inicial (Faça apenas uma vez)

Antes de começar, diga ao Git quem é você (isso anexa sua identidade aos commits):
Ou pode autenticar no navegador

```bash
git config --global user.name "Seu Nome Aqui"
git config --global user.email "seu_email@aqui.com"
```

---

## 🚀 2. Fazendo o Upload (Enviando seu projeto)

Use este fluxo quando você criou um projeto na sua máquina e quer enviá-lo para o GitHub/GitLab pela primeira vez.

### Passo a Passo:

**1. Inicie o Git na pasta do seu projeto**
Abra o terminal na pasta do projeto e digite:
```bash
git init
```

**2. Adicione os arquivos para a "fila de envio"**
Para adicionar todos os arquivos modificados de uma vez:
```bash
git add .
```
*(Dica: o `.` significa "todos os arquivos". Se quiser adicionar só um arquivo, use `git add nome_do_arquivo.txt`)*

**3. Crie um "ponto de salvamento" (Commit)**
Sempre escreva uma mensagem clara do que foi feito:
```bash
git commit -m "Primeiro commit: criação do projeto"
```

**4. Conecte seu projeto local ao repositório online**
Vá ao GitHub, crie um repositório vazio e copie a URL. Depois, no terminal:
```bash
git remote add origin https://github.com/jeffersomsct/pktm.git
```

**5. Envie os arquivos (Push)**
Mande seu código para a internet:
```bash
git push -u origin main
```
*(Nota: se o seu branch principal se chama `master` em vez de `main`, use `master` no comando acima).*

---

## 📥 3. Resgatando o Projeto (Baixando para sua máquina)

Use este fluxo quando você está em um computador diferente e quer baixar o projeto, ou quando alguém do time fez alterações e você quer trazer para o seu computador.

### Situação A: Primeira vez na máquina (Clonar)
Se o projeto não existe no seu computador ainda, copie a URL do repositório no GitHub e digite:
```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
```
Isso criará uma pasta com todo o projeto dentro.

### Situação B: Você já tem o projeto, mas quer atualizar (Pull)
Se você já clonou o projeto antes e quer baixar as últimas atualizações feitas por outras pessoas (ou por você em outra máquina), entre na pasta do projeto pelo terminal e digite:
```bash
git pull origin main
```

---

## 🔄 4. Fluxo de Trabalho Diário (Resumo)

Depois que o repositório já está criado e sincronizado, seu dia a dia será apenas isso:

1. Você modifica arquivos no seu editor de código.
2. Adiciona as mudanças: `git add .`
3. Salva com um comentário: `git commit -m "Fix: corrigi o bug do botão"`
4. Envia para a nuvem: `git push origin main`
5. No dia seguinte, começa puxando as novidades: `git pull origin main`

---

## 💡 Dicas Extras

* **Verificar status:** Se estiver em dúvida sobre quais arquivos foram modificados ou adicionados, digite:
  ```bash
  git status
  ```
* **Arquivos que não devem ir para o GitHub:** Use um arquivo chamado `.gitignore` na raiz do seu projeto para listar arquivos e pastas que o Git deve ignorar (ex: `node_modules/`, `.env`, senhas, etc).
```

### Como usar este arquivo:
1. Crie um arquivo chamado `guia_git.md` no seu computador.
2. Cole todo o conteúdo acima dentro dele.
3. Se usar o **VS Code**, basta abri-lo e clicar no ícone de "Preview" (lupa com duas setas no canto superior direito) para ver a formatação bonita e organizada.