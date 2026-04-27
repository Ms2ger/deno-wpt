#! /usr/bin/env python3
import json
import sys
from collections import Counter

def debug(*args):
    if False:
        print(*args)

manifestpath = sys.argv[1]
debug(f"reading manifest from {manifestpath}")

outputpath = sys.argv[2]
debug(f"will write expectations.json to {outputpath}")

with open(manifestpath, "r") as f:
    manifest = json.load(f)

th = manifest["items"]["testharness"]
debug(th.keys())

EXCLUDED = [
    ".xhtml",
    ".any.js",
    ".worker.html",
    ".any.serviceworker.html",
    ".any.shadowrealm-in-dedicatedworker.html",
    ".any.shadowrealm-in-shadowrealm.html",
    ".any.shadowrealm-in-sharedworker.html",
    ".any.shadowrealm-in-window.html",
    ".any.sharedworker.html",
    ".https.any.shadowrealm-in-audioworklet.html",
    ".https.any.shadowrealm-in-serviceworker.html",
]

def filtered_append(res: list[str], path: str):
    if any(ex in path for ex in EXCLUDED):
        return
    res.append(path)

def extract_test_paths(parent, tree) -> list[str]:
    res : list[str] = []
    for path, v in tree.items():
        if isinstance(v, list):
            for test, _ in v[1:]:
                if test is None:
                    testpath = f"{parent}/{path}"
                else:
                    testpath = test
                debug(f"test: {testpath}")
                filtered_append(res, testpath)
        else:
            debug(f"subdir: {parent}/{path} {v}")
            res.extend(extract_test_paths(f"{parent}/{path}", v))
    return res

def extract_test_paths_top_level(d: str) -> list[str]:
    return extract_test_paths(d, th[d])

def find_and_insert(parent: dict, edges):
    assert edges

    if len(edges) == 1:
        parent[edges[0]] = True
        return
    if edges[0] not in parent:
        parent[edges[0]] = {}
    dir = parent[edges[0]]
    find_and_insert(dir, edges[1:])

all_paths: list[str] = []

# https://github.com/WinterTC55/proposal-minimum-common-api/issues/86

# ## AbortSignal

#     * `AbortController`

#     * `AbortSignal`


# ```
# +dom/abort/*
# -dom/abort/reason-constructor.html
# ```

# -dom/abort/abort-signal-timeout.html

dom = extract_test_paths_top_level("dom")
debug("\n".join(dom))
all_paths.extend(
    p for p in dom
    if p.startswith("dom/abort/") and p not in [
        "dom/abort/abort-signal-timeout.html",
        "dom/abort/reason-constructor.html",
    ])

# ## Web Crypto API

#     * Crypto

#     * CryptoKey

#     * SubtleCrypto

#     * globalThis.crypto


# ```
# +WebCryptoAPI/*
# -historical.any.*
# -algorithm-discards-context.https.window.*
# ```

crypto = extract_test_paths_top_level("WebCryptoAPI")
debug("\n".join(crypto))
all_paths.extend(
    p for p in crypto
    if not p.endswith("historical.any.html") and not p.endswith("algorithm-discards-context.https.window.html"))

# ## Console

#     * globalThis.console


# ```
# +console/*
# ```

# Tests are very sparse, and so is spec - it is unclear what side-effects `console.log` should have across runtimes.

console = extract_test_paths_top_level("console")
debug("\n".join(console))
all_paths.extend(console)


# ## Streams

#     * ByteLengthQueuingStrategy

#     * CountQueuingStrategy

#     * ReadableByteStreamController

#     * ReadableStream

#     * ReadableStreamBYOBReader

#     * ReadableStreamBYOBRequest

#     * ReadableStreamDefaultController

#     * ReadableStreamDefaultReader

#     * TransformStream

#     * TransformStreamDefaultController

#     * WritableStream

#     * WritableStreamDefaultController

#     * WritableStreamDefaultWriter


# ```
# +streams/*
# -streams/readable-streams/cross-realm-crash.window.html
# ```

# `streams/transferable/*` needs investigation.
# -streams/queuing-strategies-size-function-per-global.window.js (uses iframe, could perhaps be rewritten)
# -streams/transferable/window.html
# -streams/transferable/service-worker.https.html

streams = extract_test_paths_top_level("streams")
debug("\n".join(streams))
all_paths.extend(
    p for p in streams
    if p not in [
        "streams/readable-streams/cross-realm-crash.window.html",
        "streams/queuing-strategies-size-function-per-global.window.html",
        "streams/readable-streams/cross-realm-crash.window.html",
        "streams/readable-streams/global.html",
        "streams/readable-streams/owning-type-video-frame.any.html",
        "streams/readable-streams/read-task-handling.window.html",
        "streams/transferable/deserialize-error.window.html",
        "streams/transferable/service-worker.https.html",
        "streams/transferable/shared-worker.html",
        "streams/transferable/transfer-with-messageport.window.html",
        "streams/transferable/window.html",
        "streams/transferable/worker.html",
        "streams/transform-streams/invalid-realm.tentative.window.html",
    ])

# ## (De)compression streams

#     * CompressionStream

#     * DecompressionStream


# ```
# +compression/*
# ```

compression = extract_test_paths_top_level("compression")
debug("\n".join(compression))
all_paths.extend(compression)


# ## Text encoding

#     * TextDecoder

#     * TextDecoderStream

#     * TextEncoder

#     * TextEncoderStream


# ```
# +encoding/*
# -encoding/streams/realms.window.html
# -encoding/streams/invalid-realm.window.html
# -encoding/unsupported-encodings.any.* (uses XHR)
# -encoding/single-byte-decoder.window.html
# -encoding/unsupported-labels.window.html
# ```

# -encoding/big5-encoder.html
# -encoding/bom-handling.html
# -encoding/iso-2022-jp-encoder.html
# -encoding/legacy-mb-japanese/*
# -encoding/legacy-mb-korean/*
# -encoding/legacy-mb-schinese/*
# -encoding/legacy-mb-tchinese/*
# -encoding/remove-only-one-bom.html
# -encoding/sniffing.html
# -encoding/streams/invalid-realm.window.js
# -encoding/streams/realms.window.js
# -encoding/utf-32-from-win1252.html
# -encoding/utf-32.html
# -encoding/replacement-encodings.any.js (uses XHR)

encoding = extract_test_paths_top_level("encoding")
# print("html", "encoding/streams/realms.window.js" in encoding)
# print("js", "encoding/streams/realms.window.html" in encoding)
debug("\n".join(encoding))
all_paths.extend(
    p for p in encoding
    if p not in [
        "encoding/streams/realms.window.html",
        "encoding/streams/invalid-realm.window.html",
        "encoding/single-byte-decoder.window.html?document",
        "encoding/single-byte-decoder.window.html?XMLHttpRequest",
        "encoding/unsupported-labels.window.html",
        "encoding/big5-encoder.html",
        "encoding/bom-handling.html",
        "encoding/iso-2022-jp-encoder.html",
        "encoding/remove-only-one-bom.html",
        "encoding/replacement-encodings.any.html",
        "encoding/sniffing.html",
        "encoding/unsupported-encodings.any.html",
        "encoding/utf-32-from-win1252.html",
        "encoding/utf-32.html"] and
        not p.startswith("encoding/legacy-mb"))

# ## URL

#     * URL

#     * URLSearchParams


# ```
# +url/*
# -url/url-setters-a-area.window.html
# -url/a-element-origin.html
# -url/a-element.html
# -url/data-uri-fragment.html
# -url/failure.html
# ```

# -url/javascript-urls.window.js
# -url/percent-encoding.window.js
# -url/toascii.window.js (needs to be split)

# Note, a lot of tests in this directory also test using `<a>` and `<area>` tags from HTML. It would be good to split those into seperate files.
# Note: url/historical.any.js is written correctly, but Deno's setup gets `self.GLOBAL.isWindow()` wrong.
url = extract_test_paths_top_level("url")
debug("\n".join(url))
all_paths.extend(
    p for p in url
    if p not in [
        "url/a-element-origin.html",
        "url/data-uri-fragment.html",
        "url/failure.html",
        "url/javascript-urls.window.html",
        "url/percent-encoding.window.html",
        "url/toascii.window.html"] and
        not p.startswith("url/a-element.html") and
        not p.startswith("url/url-setters-a-area.window.html"))

# ## URLPattern

#     * URLPattern


# ```
# +urlpattern/urlpattern.any.*
# +urlpattern/urlpattern-https.any.*
# +urlpattern/urlpattern-hasregexpgroups.any.*
# ```

# TODO: include all

urlpattern = extract_test_paths_top_level("urlpattern")
debug("\n".join(urlpattern))
all_paths.extend(
    p for p in urlpattern)

# ## File API

#     * Blob

#     * File


# ```
# +FileAPI/blob/*
# -FileAPI/blob/Blob-constructor-dom.window.html
# +FileAPI/file/*
# -FileAPI/file/send-file-form* # omit send-file-form.html
# +FileAPI/url/url-format.any.*
# +FileAPI/url/url-with-fetch.any.*
# +FileAPI/unicode.html
# ```

# Using navigator.platform to check if we're running on Windows
# -FileAPI/blob/Blob-constructor-endings.html
# -FileAPI/file/File-constructor-endings.html

fileapi = extract_test_paths_top_level("FileAPI")
debug("\n".join(fileapi))
all_paths.extend(
    p for p in fileapi
    if
        (p.startswith("FileAPI/blob/") and not p == "FileAPI/blob/Blob-constructor-dom.window.html") or
        (p.startswith("FileAPI/file/") and not p.startswith("FileAPI/file/send-file-form")) or
        p in [
            "FileAPI/url/url-format.any.html",
            "FileAPI/url/url-with-fetch.any.html",
            "FileAPI/unicode.html"])

# ## Structured Clone

#     * `structuredClone`


# More analysis needed: to be done by [@andreubotella](https://github.com/andreubotella). [web-platform-tests/wpt#49282](https://github.com/web-platform-tests/wpt/pull/49282)
# ## DOMException

#     * `DOMException`


# ```
# +webidl/ecmascript-binding/es-exceptions/DOMException-*
# ```

webidl = extract_test_paths_top_level("webidl")
debug("\n".join(webidl))
all_paths.extend(
    p for p in webidl
    if p.startswith("webidl/ecmascript-binding/es-exceptions/DOMException-"))

# ## WASM

#     * `WebAssembly`


# ```
# +wasm/*
# -wasm/serialization/module/*
# ```

# We need to write some dedicated tests for wasm structured clone that do not involve DOM / HTML.

wasm = extract_test_paths_top_level("wasm")
debug("\n".join(wasm))
all_paths.extend(
    p for p in wasm
    if p not in [
        "wasm/jsapi/proto-from-ctor-realm.html",
        "wasm/serialization/arraybuffer/transfer.window.html",
        "wasm/webapi/historical.any.html"] and
        not p.startswith("wasm/jsapi/esm-integration/") and
        not p.startswith("wasm/jsapi/functions/") and
        not p.startswith("wasm/serialization/module/") and
        not p.startswith("wasm/webapi/esm-integration/")) # TODO confirm

# ## navigator

#     * `navigator`


# No existing tests that we can use.

# Create a new test for just `user-agent` to check it's a string. maybe also check that `fetch` sets the `user-agent` test.
# ## performance.now

#     * `performance.now`


# ```
# +hr-time/idlharness.any.*
    # Note: hr-time/idlharness.any.html checks for Window.performance
# +hr-time/basic.any.*
# +hr-time/monotonic-clock.any.*
# ```

hrtime = extract_test_paths_top_level("hr-time")
debug("\n".join(hrtime))
all_paths.extend(
    p for p in hrtime
    if p in [
        "hr-time/idlharness.any.html",
        "hr-time/basic.any.html",
        "hr-time/monotonic-clock.any.html"])

# ## queueMicrotask

#     * `queueMicrotask`


# ```
# +html/webappapis/microtask-queuing/queue-microtask.any.*
# +html/webappapis/microtask-queuing/queue-microtask-exceptions.any.*
# ```

# ## `setInterval`/`setTimeout`

#     * `setInterval`

#     * `clearInterval`

#     * `setTimeout`

#     * `clearTimeout`


# ```
# +html/webappapis/timers/*
# -html/webappapis/timers/setinterval-cross-realm-callback-report-exception.html
# -html/webappapis/timers/settimeout-cross-realm-callback-report-exception.html
# ```

# ## `atob`/`btoa`

#     * `atob`

#     * `btoa`


# ```
# +html/webappapis/atob/*
# ```

html = extract_test_paths_top_level("html")
debug("\n".join(html))
all_paths.extend(
    p for p in html
    if p in [
        "html/webappapis/microtask-queuing/queue-microtask.any.html",
        "html/webappapis/microtask-queuing/queue-microtask-exceptions.any.html"] or
    (p.startswith("html/webappapis/timers/") and not p.endswith("cross-realm-callback-report-exception.html")) or
    p.startswith("html/webappapis/atob/"))


# ## `FormData`

# (`constructor.any.js` depends on what we decide to do with the arguments, see [#63](https://github.com/WinterTC55/proposal-minimum-common-api/issues/63))

# ```
# +xhr/formdata
# -xhr/formdata/append-formelement.html
# -xhr/formdata/constructor-formelement.html
# -xhr/formdata/constructor-submitter-coordinate.html
# -xhr/formdata/constructor-submitter.html
# -xhr/formdata/delete-formelement.html
# -xhr/formdata/get-formelement.html
# -xhr/formdata/has-formelement.html
# -xhr/formdata/set-formelement.html
# ```

xhr = extract_test_paths_top_level("xhr")
debug("XHR:")
debug("\n".join(xhr))
all_paths.extend(
    p for p in xhr
    if p.startswith("xhr/formdata/") and p not in [
        "xhr/formdata/append-formelement.html",
        "xhr/formdata/constructor-formelement.html",
        "xhr/formdata/constructor-submitter-coordinate.html",
        "xhr/formdata/constructor-submitter.html",
        "xhr/formdata/delete-formelement.html",
        "xhr/formdata/get-formelement.html",
        "xhr/formdata/has-formelement.html",
        "xhr/formdata/set-formelement.html",
        "xhr/formdata/submitter-coordinate-value.html"])


# debug("\n".join(all_paths))
counter = Counter(
    "any" if path.endswith(".any.js")
    else "any.html" if path.endswith(".any.html")
    else "wast.js.html" if path.endswith(".wast.js.html")
    else "html" if path.endswith(".html")
    else "xhtml" if path.endswith(".xhtml")
    else "worker" if path.endswith(".worker.js")
    else "window" if path.endswith(".window.js")
    else path#.rsplit(".")[-1]
    for path in (path.rsplit("?")[0] for path in all_paths)
)
debug(counter)
debug("Done")

tree = {}
for path in all_paths:
    # debug(path)
    find_and_insert(tree, path.split("/"))
    # debug(tree)
    # debug(80 * "-")
debug(tree)
if outputpath == "-":
    print(tree)
else:
    with open(outputpath, "w") as fp:
        json.dump(tree, fp, indent=2, separators=(',', ': '), sort_keys=True)
