package com.novibe.common.data_sources;

import com.novibe.common.util.Log;
import org.springframework.stereotype.Service;

import java.util.regex.Pattern;
import java.util.stream.Stream;

@Service
public class HostsOverrideListsLoader extends ListLoader<HostsOverrideListsLoader.BypassRoute> {

    public record BypassRoute(String ip, String website) {
    }

    @Override
    protected Stream<BypassRoute> lineParser(String urlList) {
        return Pattern.compile("\\r?\\n").splitAsStream(urlList)
                .parallel()
                .map(String::strip)
                .filter(str -> !str.isBlank())
                .filter(line -> !line.startsWith("#"))
                .filter(line -> !HostsBlockListsLoader.isBlock(line))
                .flatMap(this::mapLine);
    }

    @Override
    protected String listType() {
        return "Override";
    }

    private Stream<BypassRoute> mapLine(String line) {
        String[] parts = line.split("\\s+", 2);
        if (parts.length < 2 || parts[1].isBlank()) {
            Log.io("Skipping malformed override line: " + line);
            return Stream.empty();
        }
        return Stream.of(new BypassRoute(parts[0], parts[1]));
    }

}
