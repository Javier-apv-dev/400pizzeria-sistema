// Aviso sonoro breve ("ding-dong") generado con Web Audio, sin archivos de audio.
// Los navegadores solo permiten reproducir sonido después de una interacción:
// el audio se habilita con el primer clic o tecla del usuario en la página.

let contexto = null

function obtenerContexto() {
  if (!contexto) {
    const Contexto = window.AudioContext || window.webkitAudioContext
    if (!Contexto) return null
    contexto = new Contexto()
  }
  return contexto
}

function habilitarAudio() {
  obtenerContexto()?.resume()
}

window.addEventListener('pointerdown', habilitarAudio, { once: true })
window.addEventListener('keydown', habilitarAudio, { once: true })

export function sonarAviso() {
  const ctx = obtenerContexto()
  // Sin interacción previa el navegador mantiene el audio suspendido: no suena
  if (!ctx || ctx.state !== 'running') return

  const inicio = ctx.currentTime
  ;[[880, 0], [660, 0.18]].forEach(([frecuencia, retraso]) => {
    const oscilador = ctx.createOscillator()
    const volumen = ctx.createGain()
    oscilador.type = 'sine'
    oscilador.frequency.value = frecuencia
    volumen.gain.setValueAtTime(0.0001, inicio + retraso)
    volumen.gain.exponentialRampToValueAtTime(0.3, inicio + retraso + 0.02)
    volumen.gain.exponentialRampToValueAtTime(0.0001, inicio + retraso + 0.35)
    oscilador.connect(volumen).connect(ctx.destination)
    oscilador.start(inicio + retraso)
    oscilador.stop(inicio + retraso + 0.4)
  })
}
