package br.com.wesley.conciliacao;

import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class ConciliadorTest {

    private final Conciliador conciliador = new Conciliador();

    @Test
    void deveClassificarEManterAOrdemDoContrato() {
        var esperados = List.of(
            new Lancamento("pag-2", 2_000L),
            new Lancamento("pag-1", 1_000L),
            new Lancamento("pag-3", 3_000L)
        );
        var liquidados = List.of(
            new Lancamento("pag-4", 4_000L),
            new Lancamento("pag-1", 900L),
            new Lancamento("pag-2", 2_000L)
        );

        var resultado = conciliador.conciliar(esperados, liquidados);

        assertEquals(List.of(
            new Resultado("pag-2", Status.CONCILIADO),
            new Resultado("pag-1", Status.VALOR_DIVERGENTE),
            new Resultado("pag-3", Status.NAO_LIQUIDADO),
            new Resultado("pag-4", Status.NAO_PREVISTO)
        ), resultado);
    }

    @Test
    void deveRejeitarReferenciaDuplicadaMesmoComValorIgual() {
        var liquidados = List.of(
            new Lancamento("pag-1", 1_000L),
            new Lancamento("pag-1", 1_000L)
        );

        assertThrows(IllegalArgumentException.class,
            () -> conciliador.conciliar(List.of(), liquidados));
    }

    @Test
    void deveRetornarListaNaoModificavel() {
        var resultado = conciliador.conciliar(
            List.of(new Lancamento("pag-1", 1_000L)),
            List.of()
        );

        assertThrows(UnsupportedOperationException.class,
            () -> resultado.add(
                new Resultado("pag-2", Status.NAO_PREVISTO)
            ));
    }
}
