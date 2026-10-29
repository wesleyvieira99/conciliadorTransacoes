# Conciliador de pagamentos de fatura

Solução do **Desafio #03**, em **Java 17**, com testes **JUnit 5** e um ebook para quem está começando. O conciliador compara um único lote de pagamentos esperados e liquidados, identifica divergências e devolve um resultado por referência.

É um exercício fictício inspirado no contexto de um banco digital, **não uma questão oficial do Nubank**. A referência identifica um pagamento, não a fatura inteira. O projeto não atualiza saldos, não recebe dinheiro e não se conecta a bancos ou parceiros.

## Comece por aqui

1. Leia este README para executar o projeto.
2. Abra o [ebook em PDF](docs/ebook.pdf) para estudar a solução com calma.
3. Use o [ebook em HTML](docs/ebook.html) para navegar pelos capítulos no navegador: baixe o arquivo e abra-o localmente. O GitHub mostra o código HTML quando você abre esse link diretamente.
4. O [texto do ebook](docs/ebook.md) e o [enunciado original](docs/enunciado.txt) também ficam disponíveis no repositório.

O ebook explica como transformar o enunciado em decisões pequenas, acompanha um lote completo e comenta **cada linha não vazia dos cinco arquivos Java da solução e do `pom.xml`**. Inclui TDD, testes, complexidade, erros comuns e exercícios resolvidos. A apresentação não depende de uma conta ou serviço externo.

## Executar do zero

Você precisa de um **JDK 17 ou superior** e de Git para clonar. O JDK fornece tanto `java` quanto `javac`; somente um ambiente de execução não basta para compilar. Confira:

```sh
java -version
javac -version
```

Clone e entre na pasta:

```sh
git clone https://github.com/wesleyvieira99/conciliadorTransacoes.git
cd conciliadorTransacoes
```

No macOS/Linux:

```sh
./mvnw clean verify
java -jar target/conciliador-transacoes-1.0.0.jar
```

No Windows, usando PowerShell:

```powershell
.\mvnw.cmd clean verify
java -jar target/conciliador-transacoes-1.0.0.jar
```

O Maven Wrapper incluído no repositório baixa a versão de Maven configurada. **Na primeira execução, é necessária internet** para baixar o Maven e as dependências de teste. O conciliador e o exemplo executável usam apenas a biblioteca padrão do Java; JUnit existe somente nos testes. Se você já tem Maven instalado, `mvn clean verify` também funciona.

Saída do exemplo:

```text
pag-2 -> CONCILIADO
pag-1 -> VALOR_DIVERGENTE
pag-3 -> NAO_LIQUIDADO
pag-4 -> NAO_PREVISTO
```

`verify` compila, executa os testes e gera o JAR. Os relatórios de teste ficam em `target/surefire-reports/`. Não é necessário configurar banco, porta HTTP, variável de integração ou framework.

## As quatro respostas possíveis

| Existe nos esperados? | Existe nos liquidados? | Valores | Status |
| --- | --- | --- | --- |
| Sim | Sim | Iguais | `CONCILIADO` |
| Sim | Sim | Diferentes | `VALOR_DIVERGENTE` |
| Sim | Não | Não há comparação | `NAO_LIQUIDADO` |
| Não | Sim | Não há comparação | `NAO_PREVISTO` |

Os valores são centavos em `long`: `1_000L` representa R$ 10,00. O código não soma nem subtrai valores; compara os inteiros recebidos, sem `double` ou arredondamento.

## Usar o núcleo em outro código Java

```java
import br.com.wesley.conciliacao.Conciliador;
import br.com.wesley.conciliacao.Lancamento;
import br.com.wesley.conciliacao.Resultado;
import java.util.List;

List<Resultado> resultados = new Conciliador().conciliar(
    List.of(new Lancamento("pag-1", 10_000L)),
    List.of(new Lancamento("pag-1", 9_000L))
);
// [Resultado[referencia=pag-1, status=VALOR_DIVERGENTE]]
```

Esse trecho deve ficar dentro de um método ou de uma sessão JShell com as classes do projeto no classpath. O exemplo completo com `main` está em [`ExemploConciliacao.java`](src/main/java/br/com/wesley/conciliacao/ExemploConciliacao.java).

## Contrato e decisões

- A saída contém exatamente uma entrada para cada referência da união das duas listas.
- Primeiro vêm os esperados na ordem original; depois, somente os liquidados exclusivos, também na ordem original.
- Duas listas vazias são válidas e produzem uma lista vazia.
- Lista ou elemento nulo, referência nula/em branco, valor menor ou igual a zero e referência repetida na mesma lista causam `IllegalArgumentException`.
- Duplicata continua inválida quando os valores são iguais. A mesma referência uma vez em cada lado é válida.
- A comparação de referência é exata: `pag-1`, `PAG-1` e ` pag-1 ` são referências diferentes. O serviço usa `String.isBlank()` para recusar texto em branco e não executa `trim()` nem normalização.
- A validação é feita no serviço. Os records são portadores de dados e não rejeitam entradas no construtor.
- As duas listas são validadas e indexadas antes de construir resultados. A primeira irregularidade interrompe a chamada; não há retorno parcial nem coleta de todos os erros.
- As entradas não são modificadas. A saída usa `List.copyOf` e não permite inclusão, remoção ou substituição de elementos.
- O serviço não possui campos mutáveis, armazenamento externo ou concorrência interna. Os dados auxiliares pertencem a cada chamada. O contrato não inclui alterações concorrentes das listas pelo chamador.

## Como o algoritmo funciona

1. `indexarEValidar` valida cada lado e cria um `LinkedHashMap<String, Long>`.
2. `validarLancamento` concentra as regras de uma entrada; `putIfAbsent` detecta referências repetidas dentro daquele lado.
3. `conciliar` percorre o índice dos esperados e usa `classificar` para decidir o status.
4. Um segundo percurso inclui os liquidados que não existem nos esperados.
5. `List.copyOf` entrega a lista final não modificável.

`LinkedHashMap` combina consulta por chave com ordem de inserção. Não há busca completa da outra lista para cada pagamento, nem ordenação alfabética.

Para `n` esperados e `m` liquidados, o tempo **médio** é `O(n + m)` e a memória adicional é `O(n + m)`, considerando custo limitado para as referências. A leitura, o hash e a comparação de strings também dependem do tamanho do texto. Essa é uma análise do algoritmo, não uma promessa de latência medida.

## Organização dos arquivos

```text
src/main/java/br/com/wesley/conciliacao/
  Lancamento.java          dados de entrada
  Resultado.java           dados de saída
  Status.java              quatro classificações
  Conciliador.java         regras do lote, sem entrada/saída externa
  ExemploConciliacao.java  adaptador local: cria dados e imprime o resultado
src/test/java/br/com/wesley/conciliacao/
  ConciliadorTest.java          os três testes iniciais do desafio
  ConciliadorContratoTest.java  cobertura complementar do contrato
.mvn/wrapper/              configuração do Maven Wrapper
mvnw / mvnw.cmd            execução de Maven no macOS/Linux e Windows
pom.xml                   versão Java, build e dependência de testes
docs/                     ebook, anotações de linhas e enunciado
scripts/                  geração reproduzível do ebook
```

**Validação realizada:** 96 execuções de teste aprovadas, sem falhas ou erros, em OpenJDK 17.0.18 e Maven 3.9.9; o JAR também foi executado com Java 17 e produziu os quatro resultados mostrados acima.

Os testes iniciais receberam somente a declaração de pacote; suas expectativas foram preservadas. A suíte complementar verifica validações nos dois lados, ordem, limites de `long`, comparação exata, preservação das entradas, saída não modificável e independência entre chamadas.

## Onde entraria a cloud? (duas frases)

Um adaptador consumidor de mensagens receberia o lote de uma fila, converteria o payload em `List<Lancamento>` e chamaria `Conciliador.conciliar`. Desserialização, confirmação da mensagem, repetição e tratamento de transporte ficariam nesse adaptador, fora do serviço, para manter as regras de conciliação independentes da infraestrutura.

O adaptador não foi implementado, conforme o escopo do desafio. O programa local imprime resultados; o núcleo não imprime, não acessa rede e não conhece filas.

## Se aparecer um erro

| Sintoma | O que conferir |
| --- | --- |
| `java` ou `javac` não encontrado | Instale um JDK e confira o `PATH` e o `JAVA_HOME`. |
| `release version 17 not supported` | `./mvnw -version` precisa mostrar um Java 17 ou superior; Maven pode estar usando outro JDK. |
| `Permission denied: ./mvnw` | No macOS/Linux, execute `chmod +x mvnw` e tente novamente. |
| Falha ao baixar Maven ou JUnit | Confira conexão, proxy e acesso aos repositórios Maven; não é uma falha da conciliação. |
| `Unable to access jarfile` | Execute `./mvnw clean verify` na raiz e confirme o nome em `target/`. |
| `NullPointerException` ao criar um teste com `List.of(null)` | `List.of` proíbe elementos nulos antes de chamar o serviço; use `Arrays.asList` ou uma lista mutável para testar essa validação. |
| Importação das classes em vermelho na IDE | Abra a pasta que contém `pom.xml`, selecione JDK 17+ e importe/recarregue o projeto Maven. O pacote é `br.com.wesley.conciliacao`. |

## Fontes

- [Java 17: records](https://docs.oracle.com/en/java/javase/17/language/records.html)
- [Java 17: LinkedHashMap](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/LinkedHashMap.html)
- [Java 17: List.copyOf](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/List.html#copyOf(java.util.Collection))
- [Java 17: String.isBlank](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/String.html#isBlank())
- [JUnit 5.11.4: guia oficial](https://docs.junit.org/5.11.4/user-guide/)
- [Maven Wrapper](https://maven.apache.org/wrapper/)

As dependências têm versões fixadas para tornar o exercício reproduzível. Não há alegação de que sejam as versões mais recentes disponíveis.

## Atualizar o ebook

Os arquivos `ebook.pdf`, `ebook.html` e `ebook.md` são versões prontas para leitura. Para regenerá-los, instale Python 3.10+, [Pandoc](https://pandoc.org/installing.html) e as dependências de documentação em um ambiente virtual:

```sh
python3 -m venv .venv-docs
.venv-docs/bin/python -m pip install -r scripts/requirements-docs.txt
.venv-docs/bin/python scripts/gerar_ebook.py
```

No Windows, o executável do ambiente fica em `.venv-docs\Scripts\python.exe`. Essas ferramentas são necessárias apenas para editar o livro, não para compilar ou executar o desafio.

Edite `docs/manuscrito.md` para alterar os capítulos. `docs/linhas.json` contém as explicações por linha; `docs/fontes-codigo.json` registra o SHA-256 dos seis arquivos comentados. Se mudar o Java ou o `pom.xml`, revise primeiro as explicações e atualize esse registro: o gerador interrompe a execução quando detecta código diferente ou linhas sem explicação, evitando publicar um livro desalinhado com a solução. O PDF usa as fontes Bitstream Vera distribuídas pelo ReportLab, sem buscar fontes na internet.
