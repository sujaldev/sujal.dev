let ws = new WebSocket("/ws");

ws.onmessage = () => {
    window.location.reload()
};

ws.onclose = async () => {
    while (true) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        try {
            const res = await fetch("/ws");
            if (res.ok) break;
        } catch (e) {
            console.log(e);
        }
    }
    window.location.reload();
}
