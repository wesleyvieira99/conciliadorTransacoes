package br.com.wesley.conciliacao;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;
import java.util.stream.LongStream;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ConciliadorContratoTest {

    private final Conciliador conciliador = new Conciliador();

    @Test
    void deveAceitarDuasListasVazias() {
        assertTrue(conciliador.conciliar(List.of(), List.of()).isEmpty());
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("classificacoes")
    void deveAplicarCadaClassificacao(
            String cenario,
            List<Lancamento> esperados,
            List<Lancamento> liquidados,
            Status status) {
        assertEquals(
            List.of(new Resultado("pag-1", status)),
            conciliador.conciliar(esperados, liquidados)
        );
    }

    static Stream<Arguments> classificacoes() {
        return Stream.of(
            Arguments.of("mesma referência e mesmo valor",
                List.of(new Lancamento("pag-1", 1_000L)),
                List.of(new Lancamento("pag-1", 1_000L)),
                Status.CONCILIADO),
            Arguments.of("mesma referência e valores diferentes",
                List.of(new Lancamento("pag-1", 1_000L)),
                List.of(new Lancamento("pag-1", 900L)),
                Status.VALOR_DIVERGENTE),
            Arguments.of("somente esperado",
                List.of(new Lancamento("pag-1", 1_000L)),
                List.of(),
                Status.NAO_LIQUIDADO),
            Arguments.of("somente liquidado",
                List.of(),
                List.of(new Lancamento("pag-1", 1_000L)),
                Status.NAO_PREVISTO)
        );
    }

    @Test
    void deveManterAOrdemDosEsperadosQuandoNaoHaLiquidados() {
        var esperados = List.of(
            new Lancamento("z", 300L),
            new Lancamento("a", 100L),
            new Lancamento("m", 200L)
        );

        assertEquals(List.of(
            new Resultado("z", Status.NAO_LIQUIDADO),
            new Resultado("a", Status.NAO_LIQUIDADO),
            new Resultado("m", Status.NAO_LIQUIDADO)
        ), conciliador.conciliar(esperados, List.of()));
    }

    @Test
    void deveManterAOrdemDosLiquidadosQuandoNaoHaEsperados() {
        var liquidados = List.of(
            new Lancamento("z", 300L),
            new Lancamento("a", 100L),
            new Lancamento("m", 200L)
        );

        assertEquals(List.of(
            new Resultado("z", Status.NAO_PREVISTO),
            new Resultado("a", Status.NAO_PREVISTO),
            new Resultado("m", Status.NAO_PREVISTO)
        ), conciliador.conciliar(List.of(), liquidados));
    }

    @Test
    void deveAcrescentarSomenteOsLiquidadosExclusivosNaOrdemDeChegada() {
        var esperados = List.of(
            new Lancamento("z", 100L),
            new Lancamento("a", 200L),
            new Lancamento("m", 300L),
            new Lancamento("b", 400L)
        );
        var liquidados = List.of(
            new Lancamento("extra-z", 1L),
            new Lancamento("m", 301L),
            new Lancamento("extra-a", 2L),
            new Lancamento("z", 100L),
            new Lancamento("extra-m", 3L),
            new Lancamento("b", 400L)
        );

        assertEquals(List.of(
            new Resultado("z", Status.CONCILIADO),
            new Resultado("a", Status.NAO_LIQUIDADO),
            new Resultado("m", Status.VALOR_DIVERGENTE),
            new Resultado("b", Status.CONCILIADO),
            new Resultado("extra-z", Status.NAO_PREVISTO),
            new Resultado("extra-a", Status.NAO_PREVISTO),
            new Resultado("extra-m", Status.NAO_PREVISTO)
        ), conciliador.conciliar(esperados, liquidados));
    }

    @ParameterizedTest
    @ValueSource(longs = {1L, 127L, 128L, 129L, 1_000L, 10_000L, 4_294_967_296L, Long.MAX_VALUE})
    void deveConciliarValoresPositivosIguaisSemDependerDoCacheDeLong(long valor) {
        var esperados = List.of(new Lancamento("pag-1", valor));
        var liquidados = List.of(new Lancamento("pag-1", valor));

        assertEquals(List.of(new Resultado("pag-1", Status.CONCILIADO)),
            conciliador.conciliar(esperados, liquidados));
    }

    @ParameterizedTest
    @MethodSource("valoresDivergentes")
    void deveDistinguirValoresDiferentesSemOverflowOuConversaoParaInt(
            long esperado, long liquidado) {
        assertEquals(List.of(new Resultado("pag-1", Status.VALOR_DIVERGENTE)),
            conciliador.conciliar(
                List.of(new Lancamento("pag-1", esperado)),
                List.of(new Lancamento("pag-1", liquidado))
            ));
    }

    static Stream<Arguments> valoresDivergentes() {
        return Stream.of(
            Arguments.of(1L, 2L),
            Arguments.of(127L, 128L),
            Arguments.of(1_000L, 900L),
            Arguments.of(1L, 4_294_967_297L),
            Arguments.of(4_294_967_297L, 1L),
            Arguments.of(Long.MAX_VALUE, Long.MAX_VALUE - 1L),
            Arguments.of(Long.MAX_VALUE - 1L, Long.MAX_VALUE),
            Arguments.of(Long.MAX_VALUE, 1L)
        );
    }

    @ParameterizedTest
    @EnumSource(Lado.class)
    void deveRejeitarListaNulaEmCadaLado(Lado lado) {
        assertThrows(IllegalArgumentException.class,
            () -> conciliarNoLado(lado, null));
    }

    @Test
    void deveRejeitarAsDuasListasNulas() {
        assertThrows(IllegalArgumentException.class,
            () -> conciliador.conciliar(null, null));
    }

    @ParameterizedTest
    @EnumSource(Lado.class)
    void deveRejeitarElementoNuloEmCadaLado(Lado lado) {
        List<Lancamento> lote = Arrays.asList(
            new Lancamento("valido", 100L), null);

        assertThrows(IllegalArgumentException.class,
            () -> conciliarNoLado(lado, lote));
    }

    @ParameterizedTest(name = "{0}: referência inválida #{index}")
    @MethodSource("referenciasInvalidas")
    void deveRejeitarReferenciasNulasOuEmBrancoNoServico(Lado lado, String referencia) {
        // A construção fica fora do assertThrows: o record é passivo.
        var invalido = new Lancamento(referencia, 100L);
        var lote = List.of(new Lancamento("valido", 200L), invalido);

        assertThrows(IllegalArgumentException.class,
            () -> conciliarNoLado(lado, lote));
    }

    static Stream<Arguments> referenciasInvalidas() {
        return Arrays.stream(Lado.values()).flatMap(lado ->
            Stream.<String>of(null, "", " ", "   ", "\t", "\n", "\r\n", "\u2003")
                .map(referencia -> Arguments.of(lado, referencia))
        );
    }

    @ParameterizedTest(name = "{0}: valor {1}")
    @MethodSource("valoresInvalidos")
    void deveRejeitarValoresNaoPositivosNoServico(Lado lado, long valor) {
        var invalido = new Lancamento("invalido", valor);
        var lote = List.of(new Lancamento("valido", 100L), invalido);

        assertThrows(IllegalArgumentException.class,
            () -> conciliarNoLado(lado, lote));
    }

    static Stream<Arguments> valoresInvalidos() {
        return Arrays.stream(Lado.values()).flatMap(lado ->
            LongStream.of(0L, -1L, -100L, Long.MIN_VALUE)
                .mapToObj(valor -> Arguments.of(lado, valor))
        );
    }

    @ParameterizedTest(name = "{0}: duplicados com valores {1} e {2}")
    @MethodSource("duplicados")
    void deveRejeitarReferenciaRepetidaEmCadaLado(
            Lado lado, long primeiroValor, long segundoValor) {
        var lote = List.of(
            new Lancamento("duplicado", primeiroValor),
            new Lancamento("intermediario", 10L),
            new Lancamento("duplicado", segundoValor)
        );

        assertThrows(IllegalArgumentException.class,
            () -> conciliarNoLado(lado, lote));
    }

    static Stream<Arguments> duplicados() {
        return Arrays.stream(Lado.values()).flatMap(lado -> Stream.of(
            Arguments.of(lado, 1_000L, 1_000L),
            Arguments.of(lado, 1_000L, 900L),
            Arguments.of(lado, Long.MAX_VALUE, Long.MAX_VALUE),
            Arguments.of(lado, Long.MAX_VALUE, 1L)
        ));
    }

    @Test
    void deveCompararReferenciasExatamenteSemTrimOuAlteracaoDeMaiusculas() {
        var esperados = List.of(
            new Lancamento("pag-1", 100L),
            new Lancamento("PAG-1", 200L),
            new Lancamento(" pag-1", 300L),
            new Lancamento("pag-1 ", 400L)
        );
        var liquidados = List.of(
            new Lancamento("pag-1 ", 400L),
            new Lancamento("Pag-1", 500L),
            new Lancamento("pag-1", 100L),
            new Lancamento(" PAG-1 ", 600L)
        );

        assertEquals(List.of(
            new Resultado("pag-1", Status.CONCILIADO),
            new Resultado("PAG-1", Status.NAO_LIQUIDADO),
            new Resultado(" pag-1", Status.NAO_LIQUIDADO),
            new Resultado("pag-1 ", Status.CONCILIADO),
            new Resultado("Pag-1", Status.NAO_PREVISTO),
            new Resultado(" PAG-1 ", Status.NAO_PREVISTO)
        ), conciliador.conciliar(esperados, liquidados));
    }

    @Test
    void deveAceitarReferenciaComEspacosETextoPreservandoSeuConteudo() {
        String referencia = " \tpag-1\n ";
        assertEquals(List.of(new Resultado(referencia, Status.CONCILIADO)),
            conciliador.conciliar(
                List.of(new Lancamento(referencia, 100L)),
                List.of(new Lancamento(referencia, 100L))
            ));
    }

    @Test
    void deveDistinguirReferenciasMesmoQuandoSeusHashesCoincidem() {
        assertEquals("Aa".hashCode(), "BB".hashCode());

        assertEquals(List.of(
            new Resultado("Aa", Status.CONCILIADO),
            new Resultado("BB", Status.VALOR_DIVERGENTE)
        ), conciliador.conciliar(
            List.of(new Lancamento("Aa", 100L), new Lancamento("BB", 200L)),
            List.of(new Lancamento("BB", 201L), new Lancamento("Aa", 100L))
        ));
    }

    @ParameterizedTest(name = "esperados {0}, liquidados {1}")
    @MethodSource("tiposDeListas")
    void devePreservarAsEntradasMutaveisAoConciliar(
            TipoLista tipoEsperados, TipoLista tipoLiquidados) {
        var esperados = tipoEsperados.copiar(List.of(
            new Lancamento("z", 200L), new Lancamento("a", 100L)));
        var liquidados = tipoLiquidados.copiar(List.of(
            new Lancamento("extra", 300L), new Lancamento("z", 201L)));
        var esperadosAntes = new ArrayList<>(esperados);
        var liquidadosAntes = new ArrayList<>(liquidados);

        var resultado = conciliador.conciliar(esperados, liquidados);

        assertEquals(List.of(
            new Resultado("z", Status.VALOR_DIVERGENTE),
            new Resultado("a", Status.NAO_LIQUIDADO),
            new Resultado("extra", Status.NAO_PREVISTO)
        ), resultado);
        assertEquals(esperadosAntes, esperados);
        assertEquals(liquidadosAntes, liquidados);
    }

    @ParameterizedTest(name = "esperados {0}, liquidados {1}, inválido em {2}")
    @MethodSource("tiposDeListasELadosInvalidos")
    void devePreservarAsEntradasMutaveisQuandoHaErro(
            TipoLista tipoEsperados, TipoLista tipoLiquidados, Lado ladoInvalido) {
        var esperados = tipoEsperados.copiar(List.of(
            new Lancamento("z", 200L), new Lancamento("a", 100L)));
        var liquidados = tipoLiquidados.copiar(List.of(
            new Lancamento("extra", 300L),
            new Lancamento("z", 201L)));
        if (ladoInvalido == Lado.ESPERADOS) {
            esperados.add(new Lancamento("z", 200L));
        } else {
            liquidados.add(new Lancamento("extra", 400L));
        }
        var esperadosAntes = new ArrayList<>(esperados);
        var liquidadosAntes = new ArrayList<>(liquidados);

        assertThrows(IllegalArgumentException.class,
            () -> conciliador.conciliar(esperados, liquidados));

        assertEquals(esperadosAntes, esperados);
        assertEquals(liquidadosAntes, liquidados);
    }

    static Stream<Arguments> tiposDeListas() {
        return Arrays.stream(TipoLista.values()).flatMap(esperados ->
            Arrays.stream(TipoLista.values())
                .map(liquidados -> Arguments.of(esperados, liquidados))
        );
    }

    static Stream<Arguments> tiposDeListasELadosInvalidos() {
        return Arrays.stream(TipoLista.values()).flatMap(esperados ->
            Arrays.stream(TipoLista.values()).flatMap(liquidados ->
                Arrays.stream(Lado.values())
                    .map(lado -> Arguments.of(esperados, liquidados, lado))
            )
        );
    }

    @ParameterizedTest
    @EnumSource(Modificacao.class)
    void deveRejeitarModificacaoDaListaNaoVaziaRetornada(Modificacao modificacao) {
        var resultado = conciliador.conciliar(
            List.of(new Lancamento("pag-1", 100L)),
            List.of(new Lancamento("pag-2", 200L)));
        var antes = List.copyOf(resultado);

        assertThrows(UnsupportedOperationException.class, () -> {
            switch (modificacao) {
                case ADICIONAR -> resultado.add(new Resultado("novo", Status.NAO_PREVISTO));
                case REMOVER -> resultado.remove(0);
                case SUBSTITUIR -> resultado.set(0, new Resultado("outro", Status.CONCILIADO));
                case LIMPAR -> resultado.clear();
            }
        });

        assertEquals(antes, resultado);
    }

    @Test
    void deveManterChamadasIndependentesEResultadosAnterioresEstaveis() {
        var primeiro = conciliador.conciliar(
            List.of(new Lancamento("reutilizada", 100L)),
            List.of(new Lancamento("reutilizada", 100L)));
        var segundo = conciliador.conciliar(
            List.of(), List.of(new Lancamento("reutilizada", 200L)));

        assertTrue(conciliador.conciliar(List.of(), List.of()).isEmpty());
        assertEquals(List.of(new Resultado("reutilizada", Status.CONCILIADO)), primeiro);
        assertEquals(List.of(new Resultado("reutilizada", Status.NAO_PREVISTO)), segundo);
        assertEquals(List.of(new Resultado("reutilizada", Status.VALOR_DIVERGENTE)),
            conciliador.conciliar(
                List.of(new Lancamento("reutilizada", 300L)),
                List.of(new Lancamento("reutilizada", 301L))));
    }

    @ParameterizedTest(name = "{0}: inválido tardio {1}")
    @MethodSource("lotesInvalidosTardios")
    void deveRejeitarLoteInteiroESeguirIndependenteDepoisDaFalha(
            Lado lado, String motivo, List<Lancamento> lote) {
        var resultadoAnterior = conciliador.conciliar(
            List.of(new Lancamento("anterior", 10L)), List.of());
        var outroLado = List.of(new Lancamento("reutilizavel", 100L));

        // Se o serviço devolver um prefixo parcial em vez de lançar, este teste falha.
        assertThrows(IllegalArgumentException.class, () -> {
            if (lado == Lado.ESPERADOS) {
                conciliador.conciliar(lote, outroLado);
            } else {
                conciliador.conciliar(outroLado, lote);
            }
        });

        assertEquals(List.of(new Resultado("anterior", Status.NAO_LIQUIDADO)),
            resultadoAnterior);
        assertEquals(List.of(new Resultado("reutilizavel", Status.CONCILIADO)),
            conciliador.conciliar(
                List.of(new Lancamento("reutilizavel", 100L)),
                List.of(new Lancamento("reutilizavel", 100L))));
        assertTrue(conciliador.conciliar(List.of(), List.of()).isEmpty());
    }

    static Stream<Arguments> lotesInvalidosTardios() {
        return Arrays.stream(Lado.values()).flatMap(lado -> Stream.of(
            Arguments.of(lado, "elemento nulo", loteComFinal(null)),
            Arguments.of(lado, "referência nula", loteComFinal(new Lancamento(null, 1L))),
            Arguments.of(lado, "referência em branco", loteComFinal(new Lancamento(" ", 1L))),
            Arguments.of(lado, "valor zero", loteComFinal(new Lancamento("ultimo", 0L))),
            Arguments.of(lado, "valor negativo", loteComFinal(new Lancamento("ultimo", -1L))),
            Arguments.of(lado, "referência duplicada",
                loteComFinal(new Lancamento("reutilizavel", 100L)))
        ));
    }

    private static List<Lancamento> loteComFinal(Lancamento ultimo) {
        return Arrays.asList(
            new Lancamento("reutilizavel", 100L),
            new Lancamento("outro", 200L),
            ultimo
        );
    }

    private List<Resultado> conciliarNoLado(Lado lado, List<Lancamento> lote) {
        return lado == Lado.ESPERADOS
            ? conciliador.conciliar(lote, List.of())
            : conciliador.conciliar(List.of(), lote);
    }

    enum Lado {
        ESPERADOS, LIQUIDADOS
    }

    enum Modificacao {
        ADICIONAR, REMOVER, SUBSTITUIR, LIMPAR
    }

    enum TipoLista {
        ARRAY_LIST, LINKED_LIST;

        List<Lancamento> copiar(List<Lancamento> origem) {
            return switch (this) {
                case ARRAY_LIST -> new ArrayList<>(origem);
                case LINKED_LIST -> new LinkedList<>(origem);
            };
        }
    }
}
