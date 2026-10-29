package br.com.wesley.conciliacao;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class Conciliador {

    public List<Resultado> conciliar(
            List<Lancamento> esperados, List<Lancamento> liquidados) {
        Map<String, Long> esperadosPorReferencia = indexarEValidar(esperados, "esperados");
        Map<String, Long> liquidadosPorReferencia = indexarEValidar(liquidados, "liquidados");

        List<Resultado> resultados = new ArrayList<>();
        for (Map.Entry<String, Long> esperado : esperadosPorReferencia.entrySet()) {
            String referencia = esperado.getKey();
            Status status = classificar(
                    esperado.getValue(), liquidadosPorReferencia.get(referencia));
            resultados.add(new Resultado(referencia, status));
        }
        for (String referencia : liquidadosPorReferencia.keySet()) {
            if (!esperadosPorReferencia.containsKey(referencia)) {
                resultados.add(new Resultado(referencia, Status.NAO_PREVISTO));
            }
        }
        return List.copyOf(resultados);
    }

    private Map<String, Long> indexarEValidar(List<Lancamento> lancamentos, String origem) {
        if (lancamentos == null) {
            throw new IllegalArgumentException(origem + ": a lista não pode ser nula.");
        }
        Map<String, Long> porReferencia = new LinkedHashMap<>();
        int indice = 0;
        for (Lancamento lancamento : lancamentos) {
            validarLancamento(lancamento, origem, indice);
            Long anterior = porReferencia.putIfAbsent(
                    lancamento.referencia(), lancamento.valorCentavos());
            if (anterior != null) {
                throw new IllegalArgumentException(
                        origem + "[" + indice + "]: referência repetida: " + lancamento.referencia());
            }
            indice++;
        }
        return porReferencia;
    }

    private void validarLancamento(Lancamento lancamento, String origem, int indice) {
        String local = origem + "[" + indice + "]";
        if (lancamento == null) {
            throw new IllegalArgumentException(local + ": o lançamento não pode ser nulo.");
        }
        String referencia = lancamento.referencia();
        if (referencia == null || referencia.isBlank()) {
            throw new IllegalArgumentException(local + ": a referência não pode ser nula ou em branco.");
        }
        if (lancamento.valorCentavos() <= 0) {
            throw new IllegalArgumentException(local + ": o valor em centavos deve ser positivo.");
        }
    }

    private Status classificar(long valorEsperado, Long valorLiquidado) {
        if (valorLiquidado == null) {
            return Status.NAO_LIQUIDADO;
        }
        return valorEsperado == valorLiquidado.longValue()
                ? Status.CONCILIADO
                : Status.VALOR_DIVERGENTE;
    }
}
