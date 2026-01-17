package com.novibe.dns.next_dns.http;

import com.novibe.common.exception.NextDnsHttpError;
import com.novibe.common.util.Log;
import com.novibe.dns.next_dns.http.dto.response.NextDnsResponse;
import lombok.SneakyThrows;
import lombok.experimental.UtilityClass;

import java.time.Duration;
import java.time.temporal.ChronoUnit;
import java.util.ArrayDeque;
import java.util.List;
import java.util.Queue;
import java.util.function.Function;

import static java.util.Optional.ofNullable;

@UtilityClass
public class NextDnsRateLimitedApiProcessor {

    private static final long REQUEST_DELAY_MS = 1000; // 1 секунда между запросами
    
    @SneakyThrows
    public <D, R extends NextDnsResponse<?>> void callApi(List<D> requestList, Function<D, R> request) {
        int waitSeconds = 60;
        Queue<D> requestQueue = new ArrayDeque<>(requestList);
        int successCounter = 0;
        int waveCounter = 0;
        while (!requestQueue.isEmpty()) {
            D requestDto = requestQueue.poll();
            try {
                R response = request.apply(requestDto);
                if (ofNullable(response).map(r -> r.getErrors()).isPresent()) {
                    Log.fail("Failed request: " + response.getErrors());
                } else {
                    Log.progress("Current success progress: " + ++successCounter + "/" + requestList.size());
                    waveCounter++;
                }
                
                // Задержка между запросами, если очередь не пуста
                if (!requestQueue.isEmpty()) {
                    Thread.sleep(REQUEST_DELAY_MS);
                }
                
            } catch (NextDnsHttpError e) {
                if (e.getCode() == 524 || e.getCode() == 429) {
                    requestQueue.add(requestDto);
                    Log.common("Sending speed: %s requests per second"
                            .formatted((double) waveCounter / 60));
                    Log.common("Code %s. Api rate limit has reached. Waiting for reset: %s seconds"
                            .formatted(e.getCode(), waitSeconds));
                    runWaitTimer(waitSeconds);
                    Log.common("Continue...");
                    waveCounter = 0;
                } else {
                    Log.fail(e.toString());
                    System.exit(1);
                }
            }
        }
    }

    @SneakyThrows
    private void runWaitTimer(int seconds) {
        Thread.sleep(Duration.of(seconds, ChronoUnit.SECONDS));
    }

}
