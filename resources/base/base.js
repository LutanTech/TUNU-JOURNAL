// window.API_URL ='http://127.00.1:5000'
window.API_URL ='https://api1.tunujournal.com'


window.getCookie = function (name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}
window.setCookie = function (name, value, days) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = `expires=${date.toUTCString()}`;
    document.cookie = `${name}=${value};${expires};path=/`;
}
window.deleteCookie = function (name) {
    document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`; 
}

document.addEventListener('DOMContentLoaded', ()=>{
    const params = new URLSearchParams(window.location.search)
    const lang = params.get('lang')

    const parent = document.querySelector('.lang-def')
    const children = document.querySelector('.lang-btns')

    const storedLang = getCookie('lang')
    if(storedLang &&!lang){
        setTimeout(() => {
            translateTo(storedLang)
        }, 3000);
        return
    }
    if(!parent || !children) return
    
    parent.addEventListener('click', () => {
        children.classList.toggle('flex')
        children.classList.toggle('none')
    })
    
    const langs = document.querySelectorAll('.l-p')
    
    langs.forEach(l => {
        if (lang) {
            const select = document.querySelector(`[lang="${lang}"]`)
            if (select) {
                setTimeout(() => {
                select.click()
                    
                }, 2000);
            }
        }
        l.addEventListener('click', () => {
    
            translateTo(l.getAttribute('lang'))
            parent.innerHTML = `  <i class="fas fa-language"></i> ${l.textContent} <i style="margin-left:10px" class="fas fa-angle-down"></i> `
            setCookie('lang', l.getAttribute('lang'))

    
            children.classList.remove('flex')
            children.classList.add('none')
    
            const langAtt = l.getAttribute('lang')
    
            params.set('lang', langAtt)
    
            const newUrl = window.location.pathname + '?' + params.toString()
    
            window.history.pushState({}, '', newUrl)
    
        })
    })

})

function googleTranslateElementInit() {
    new google.translate.TranslateElement(
        {
            pageLanguage: 'en',
            autoDisplay: false,
        },
        'google_translate_element'
    );
}

function translateTo(lang) {
    const interval = setInterval(() => {
        const select = document.querySelector(".goog-te-combo");

        if (select) {
            select.value = lang;
            select.dispatchEvent(new Event("change"));
            clearInterval(interval);
        } else{
            console.log('not found')
        }
    }, 200);
}

document.cookie = "googtrans=;path=/;";