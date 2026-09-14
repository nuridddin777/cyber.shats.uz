// ============================================================
// CYBER SHATS — WebRTC video-qo'ng'iroq (mesh, HTTP-polling signalizatsiya)
// ============================================================
(function () {
    if (typeof window.CS_CALL === 'undefined') return;
    var cfg = window.CS_CALL; // { roomCode, myId, isHost }

    var ICE_SERVERS = [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ];

    var localStream = null;
    var peers = {};          // userId -> RTCPeerConnection
    var lastSignalId = 0;
    var pollTimer = null;
    var knownParticipants = {};
    var micOn = true, camOn = true;

    function $(id) { return document.getElementById(id); }

    function addRemoteTile(userId, name) {
        if ($('tile-' + userId)) return;
        var grid = $('videoGrid');
        var tile = document.createElement('div');
        tile.className = 'call-tile';
        tile.id = 'tile-' + userId;
        tile.innerHTML = '<video id="video-' + userId + '" autoplay playsinline></video>' +
            '<div class="call-tile-name">' + name + '</div>';
        grid.appendChild(tile);
    }

    function removeRemoteTile(userId) {
        var tile = $('tile-' + userId);
        if (tile) tile.remove();
        if (peers[userId]) { peers[userId].close(); delete peers[userId]; }
    }

    async function sendSignal(toUserId, signalType, payload) {
        await fetch('/api/call/' + cfg.roomCode + '/signal', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ to_user_id: toUserId, signal_type: signalType, payload: payload })
        });
    }

    function createPeerConnection(remoteUserId) {
        var pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
        peers[remoteUserId] = pc;

        if (localStream) {
            localStream.getTracks().forEach(function (track) { pc.addTrack(track, localStream); });
        }

        pc.ontrack = function (event) {
            var el = $('video-' + remoteUserId);
            if (el) el.srcObject = event.streams[0];
        };

        pc.onicecandidate = function (event) {
            if (event.candidate) {
                sendSignal(remoteUserId, 'ice-candidate', event.candidate);
            }
        };

        pc.onconnectionstatechange = function () {
            if (pc.connectionState === 'failed' || pc.connectionState === 'closed') {
                removeRemoteTile(remoteUserId);
            }
        };

        return pc;
    }

    async function callUser(remoteUserId, name) {
        addRemoteTile(remoteUserId, name);
        var pc = createPeerConnection(remoteUserId);
        var offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        await sendSignal(remoteUserId, 'offer', offer);
    }

    async function handleOffer(fromUserId, name, offer) {
        addRemoteTile(fromUserId, name);
        var pc = createPeerConnection(fromUserId);
        await pc.setRemoteDescription(new RTCSessionDescription(offer));
        var answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        await sendSignal(fromUserId, 'answer', answer);
    }

    async function handleAnswer(fromUserId, answer) {
        var pc = peers[fromUserId];
        if (pc) await pc.setRemoteDescription(new RTCSessionDescription(answer));
    }

    async function handleIceCandidate(fromUserId, candidate) {
        var pc = peers[fromUserId];
        if (pc) {
            try { await pc.addIceCandidate(new RTCIceCandidate(candidate)); } catch (e) {}
        }
    }

    async function pollSignals() {
        try {
            var r = await fetch('/api/call/' + cfg.roomCode + '/signals?after_id=' + lastSignalId);
            var d = await r.json();
            if (!d.success) return;
            for (var i = 0; i < d.data.signals.length; i++) {
                var s = d.data.signals[i];
                lastSignalId = Math.max(lastSignalId, s.id);
                var name = (knownParticipants[s.from_user_id] || {}).name || ('#' + s.from_user_id);
                if (s.signal_type === 'offer') await handleOffer(s.from_user_id, name, s.payload);
                else if (s.signal_type === 'answer') await handleAnswer(s.from_user_id, s.payload);
                else if (s.signal_type === 'ice-candidate') await handleIceCandidate(s.from_user_id, s.payload);
                else if (s.signal_type === 'leave') removeRemoteTile(s.from_user_id);
            }
        } catch (e) { /* jim */ }
    }

    async function pollParticipants() {
        try {
            var r = await fetch('/api/call/' + cfg.roomCode + '/state');
            var d = await r.json();
            if (!d.success) return;
            d.data.participants.forEach(function (p) {
                if (p.user_id === cfg.myId) return;
                var name = p.ism + ' ' + (p.familiya || '');
                if (!knownParticipants[p.user_id]) {
                    knownParticipants[p.user_id] = { name: name };
                    // Faqat KICHIKROQ ID'li tomon boshlaydi (offer takrorlanmasligi uchun)
                    if (cfg.myId < p.user_id) callUser(p.user_id, name);
                }
            });
        } catch (e) { /* jim */ }
    }

    async function startCall() {
        try {
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            $('localVideo').srcObject = localStream;
        } catch (e) {
            $('callStatus').textContent = 'Kamera/mikrofonga ruxsat berilmadi: ' + e.message;
            return;
        }
        pollTimer = setInterval(function () { pollParticipants(); pollSignals(); }, 1500);
        pollParticipants();
    }

    function toggleMic() {
        if (!localStream) return;
        micOn = !micOn;
        localStream.getAudioTracks().forEach(function (t) { t.enabled = micOn; });
        $('micBtn').classList.toggle('off', !micOn);
    }

    function toggleCam() {
        if (!localStream) return;
        camOn = !camOn;
        localStream.getVideoTracks().forEach(function (t) { t.enabled = camOn; });
        $('camBtn').classList.toggle('off', !camOn);
    }

    function cleanup() {
        if (pollTimer) clearInterval(pollTimer);
        Object.keys(peers).forEach(function (uid) { peers[uid].close(); });
        if (localStream) localStream.getTracks().forEach(function (t) { t.stop(); });
        navigator.sendBeacon && navigator.sendBeacon('/call/' + cfg.roomCode + '/leave');
    }

    window.addEventListener('beforeunload', cleanup);
    document.addEventListener('DOMContentLoaded', function () {
        $('micBtn').addEventListener('click', toggleMic);
        $('camBtn').addEventListener('click', toggleCam);
        startCall();
    });
})();
