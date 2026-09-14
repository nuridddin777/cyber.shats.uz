/* ============================================================
   CYBER SHATS — AI Yordamchi chat interfeysi (frontend logikasi)
   Endi rasm yuklab yuborish (vision) qo'llab-quvvatlanadi.
   ============================================================ */
(function () {
    var msgsBox = document.querySelector('[data-chat-msgs]');
    var form = document.querySelector('[data-chat-form]');
    var input = document.querySelector('[data-chat-input]');
    var typeInput = document.querySelector('[data-chat-type]');
    var imageInput = document.querySelector('[data-chat-image-input]');
    var imageBtn = document.querySelector('[data-chat-image-btn]');
    var imagePreview = document.querySelector('[data-chat-image-preview]');
    if (!form || !msgsBox) return;

    var MAX_IMAGES = 4;
    var MAX_BYTES = 5 * 1024 * 1024;
    var pendingImages = []; // {media_type, data (base64, no prefix), previewUrl}

    function addMsg(role, text, imageUrls) {
        var div = document.createElement('div');
        div.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
        (imageUrls || []).forEach(function (url) {
            var img = document.createElement('img');
            img.className = 'msg-img';
            img.src = url;
            div.appendChild(img);
        });
        var textNode = document.createElement('div');
        textNode.textContent = text;
        div.appendChild(textNode);
        msgsBox.appendChild(div);
        msgsBox.scrollTop = msgsBox.scrollHeight;
        return div;
    }

    function addTyping() {
        var div = document.createElement('div');
        div.className = 'msg bot typing-dots';
        div.innerHTML = '<span></span><span></span><span></span>';
        msgsBox.appendChild(div);
        msgsBox.scrollTop = msgsBox.scrollHeight;
        return div;
    }

    function renderPreview() {
        if (!imagePreview) return;
        imagePreview.innerHTML = '';
        if (!pendingImages.length) {
            imagePreview.style.display = 'none';
            if (imageBtn) imageBtn.classList.remove('has-image');
            return;
        }
        imagePreview.style.display = 'flex';
        if (imageBtn) imageBtn.classList.add('has-image');
        pendingImages.forEach(function (img, idx) {
            var thumb = document.createElement('div');
            thumb.className = 'thumb';
            var imEl = document.createElement('img');
            imEl.src = img.previewUrl;
            var rm = document.createElement('div');
            rm.className = 'rm';
            rm.textContent = '\u00d7';
            rm.addEventListener('click', function () {
                pendingImages.splice(idx, 1);
                renderPreview();
            });
            thumb.appendChild(imEl);
            thumb.appendChild(rm);
            imagePreview.appendChild(thumb);
        });
    }

    if (imageBtn && imageInput) {
        imageBtn.addEventListener('click', function () {
            imageInput.click();
        });
        imageInput.addEventListener('change', function () {
            var files = Array.prototype.slice.call(imageInput.files || []);
            imageInput.value = '';
            files.forEach(function (file) {
                if (pendingImages.length >= MAX_IMAGES) return;
                if (!file.type || file.type.indexOf('image/') !== 0) return;
                if (file.size > MAX_BYTES) {
                    addMsg('assistant', "Rasm hajmi 5 MB dan katta bo'lmasligi kerak: " + file.name);
                    return;
                }
                var reader = new FileReader();
                reader.onload = function (e) {
                    var dataUrl = e.target.result; // data:image/png;base64,AAAA...
                    var comma = dataUrl.indexOf(',');
                    var base64 = dataUrl.slice(comma + 1);
                    pendingImages.push({
                        media_type: file.type,
                        data: base64,
                        previewUrl: dataUrl
                    });
                    renderPreview();
                };
                reader.readAsDataURL(file);
            });
        });
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        var text = (input.value || '').trim();
        var imagesToSend = pendingImages.slice();
        if (!text && !imagesToSend.length) return;

        addMsg('user', text, imagesToSend.map(function (i) { return i.previewUrl; }));
        input.value = '';
        pendingImages = [];
        renderPreview();
        var typingEl = addTyping();

        fetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                type: typeInput ? typeInput.value : 'umumiy',
                images: imagesToSend.map(function (i) { return { media_type: i.media_type, data: i.data }; })
            })
        })
            .then(function (r) { return r.json(); })
            .then(function (res) {
                typingEl.remove();
                if (res.success) {
                    addMsg('assistant', res.data.reply);
                } else {
                    addMsg('assistant', 'Xatolik yuz berdi: ' + (res.error || "noma'lum xato"));
                }
            })
            .catch(function () {
                typingEl.remove();
                addMsg('assistant', "Tarmoq xatosi yuz berdi. Internetingizni tekshirib, qayta urinib ko'ring.");
            });
    });
})();
