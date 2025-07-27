let ws = new WebSocket("/ws");

ws.onmessage = () => {
    window.location.reload()
};

ws.onclose = async () => {
    await new Promise((resolve) => setTimeout(resolve, 500));
    while (true) {
        try {
            const res = await fetch("/ws");
            if (res.ok) break;
        } catch (e) {
            console.log(e);
        }
    }
    window.location.reload();
}
