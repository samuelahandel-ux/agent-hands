import { StatusBar } from "expo-status-bar";
import { useCallback, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { WebView } from "react-native-webview";

const DEFAULT_URL =
  process.env.EXPO_PUBLIC_BASELINE_URL ??
  "https://instant-onyx-un2tipy.tmp.now";

export default function App() {
  const webRef = useRef<WebView>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const uri = useMemo(() => DEFAULT_URL, []);

  const reload = useCallback(() => {
    setError(null);
    setLoading(true);
    webRef.current?.reload();
  }, []);

  return (
    <View style={styles.root}>
      <StatusBar style="dark" />
      <SafeAreaView style={styles.safe}>
        <View style={styles.chrome}>
          <Text style={styles.brand}>Baseline</Text>
          <Pressable onPress={reload} style={styles.reloadBtn} hitSlop={12}>
            <Text style={styles.reloadText}>Refresh</Text>
          </Pressable>
        </View>

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorTitle}>Couldn’t load Baseline</Text>
            <Text style={styles.errorBody}>{error}</Text>
            <Pressable onPress={reload} style={styles.cta}>
              <Text style={styles.ctaText}>Try again</Text>
            </Pressable>
          </View>
        ) : (
          <View style={styles.webWrap}>
            <WebView
              ref={webRef}
              source={{ uri }}
              style={styles.webview}
              onLoadStart={() => setLoading(true)}
              onLoadEnd={() => setLoading(false)}
              onError={(e) => {
                setLoading(false);
                setError(e.nativeEvent.description || "Network error");
              }}
              onHttpError={(e) => {
                if (e.nativeEvent.statusCode >= 400) {
                  setError(`HTTP ${e.nativeEvent.statusCode}`);
                }
              }}
              allowsBackForwardNavigationGestures
              sharedCookiesEnabled
              thirdPartyCookiesEnabled
              setSupportMultipleWindows={false}
              applicationNameForUserAgent="BaselineiOS/1.0"
              startInLoadingState
            />
            {loading ? (
              <View style={styles.loader}>
                <ActivityIndicator size="large" color="#1a7a6a" />
              </View>
            ) : null}
          </View>
        )}
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#c8ddd6",
  },
  safe: {
    flex: 1,
    paddingTop: Platform.OS === "android" ? 12 : 0,
  },
  chrome: {
    paddingHorizontal: 18,
    paddingBottom: 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  brand: {
    fontSize: 28,
    fontWeight: "700",
    letterSpacing: -0.8,
    color: "#13211c",
  },
  reloadBtn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: "rgba(255,255,255,0.45)",
  },
  reloadText: {
    color: "#1a7a6a",
    fontWeight: "600",
    fontSize: 13,
  },
  webWrap: {
    flex: 1,
    marginHorizontal: 10,
    marginBottom: 10,
    borderRadius: 28,
    overflow: "hidden",
    backgroundColor: "rgba(255,255,255,0.35)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.45)",
  },
  webview: {
    flex: 1,
    backgroundColor: "transparent",
  },
  loader: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(200,221,214,0.55)",
  },
  errorBox: {
    flex: 1,
    margin: 18,
    borderRadius: 28,
    padding: 22,
    backgroundColor: "rgba(255,255,255,0.45)",
    justifyContent: "center",
  },
  errorTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: "#13211c",
  },
  errorBody: {
    marginTop: 8,
    color: "rgba(19,33,28,0.65)",
    lineHeight: 20,
  },
  cta: {
    marginTop: 18,
    alignSelf: "flex-start",
    backgroundColor: "#1a7a6a",
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  ctaText: {
    color: "#f4fffb",
    fontWeight: "600",
  },
});
