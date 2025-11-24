export async function getLottoHistory() {
  const url =
    "https://raw.githubusercontent.com/justyoung242/GoldenLottoV2/main/lotto_data.json";

  try {
    const response = await fetch(url, {
      headers: { "Cache-Control": "no-cache" },
    });

    if (!response.ok) {
      throw new Error("Failed to load lotto data");
    }

    return await response.json();
  } catch (err) {
    console.error("Error fetching lotto history:", err);
    return { error: "Unable to load data" };
  }
}
