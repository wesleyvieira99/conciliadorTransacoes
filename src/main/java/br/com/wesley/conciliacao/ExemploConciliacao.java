package br.com.wesley.conciliacao;

import java.util.List;

public final class ExemploConciliacao {
    public static void main(String[] args) {
        List<Lancamento> esperados = List.of(
                new Lancamento("pag-2", 2_000L),
                new Lancamento("pag-1", 1_000L),
                new Lancamento("pag-3", 3_000L));
        List<Lancamento> liquidados = List.of(
                new Lancamento("pag-4", 4_000L),
                new Lancamento("pag-1", 900L),
                new Lancamento("pag-2", 2_000L));

        Conciliador conciliador = new Conciliador();
        List<Resultado> resultados = conciliador.conciliar(esperados, liquidados);
        for (Resultado resultado : resultados) {
            System.out.println(resultado.referencia() + " -> " + resultado.status());
        }
    }
}
