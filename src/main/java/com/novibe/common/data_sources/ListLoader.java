package com.novibe.common.data_sources;

import com.novibe.common.util.Log;
import lombok.Cleanup;
import lombok.Setter;
import lombok.SneakyThrows;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Profile;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.StructuredTaskScope;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@Profile("CLOUDFLARE")
@Setter(onMethod_ = @Autowired)
public abstract class ListLoader<T> {

    private HttpClient client;

    protected abstract Stream<T> lineParser(String urlList);

    protected abstract String listType();

    @SneakyThrows
    @SuppressWarnings("preview")
    public List<T> fetchWebsites(List<String> urls) {
        @Cleanup var scope = StructuredTaskScope.open();
        List<StructuredTaskScope.Subtask<String>> requests = new ArrayList<>();
        urls.stream()
                .map(url -> scope.fork(() -> fetchList(url)))
                .forEach(requests::add);
        scope.join();
        return requests.stream()
                .map(StructuredTaskScope.Subtask::get)
                .flatMap(this::lineParser)
                .distinct()
                .collect(Collectors.toCollection(ArrayList::new));
    }

    @SneakyThrows
    private String fetchList(String url) {
        Log.io("Loading %s list from url: %s".formatted(listType(), url));
        URI uri = URI.create(url);
        if ("file".equalsIgnoreCase(uri.getScheme())) {
            return Files.readString(Path.of(uri), StandardCharsets.UTF_8);
        }
        HttpRequest request = HttpRequest.newBuilder(uri)
                .GET()
                .build();
        return client.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8)).body();
    }

}
