# Diagnóstico de captura con la tecla V

En el registro de la partida local, Unreal inicializó WASAPI repetidamente con **48.000 Hz y PCM flotante de 32 bits**. Por ejemplo, el registro marca aperturas a las 02:45:23 y 02:48:32 hora local. Las 60 entradas del historial NLP de la sesión posterior a las pruebas automatizadas corresponden a texto, con STT en cero. La evidencia ubica el fallo antes del envío de un WAV al servicio.

La implementación anterior en `YellPlayer.cpp` usaba «Captura demasiado breve o incompleta» para varios casos. Podía indicar que llegaron menos de 250 ms, que faltaron muestras, que se detectó un formato inesperado, que cambió el estado del comandante o que se activó `bCaptureFault`. WASAPI transmite una discontinuidad de un paquete mediante `bOverflow`, y el controlador anterior marcaba toda la captura como defectuosa al recibir ese aviso. La discontinuidad puede corresponder a una transición del flujo o a un salto de temporización. El historial original carecía del recuento de paquetes necesario para distinguirlos. [Significado del indicador WASAPI](https://learn.microsoft.com/windows/win32/api/audioclient/ne-audioclient-_audclnt_bufferflags).

La apertura del dispositivo sí aparece en la sesión. Para comprobar que el endpoint de entrada físico registra voz, Windows ofrece una prueba en **Configuración → Sistema → Sonido → Entrada**. El ajuste de privacidad de acceso para aplicaciones de escritorio se aplica a Unreal. [Prueba de entrada de Windows](https://support.microsoft.com/en-us/windows/hardware/drivers/how-to-set-up-and-test-microphones-in-windows), [permisos de micrófono](https://support.microsoft.com/en-us/windows/privacy/turn-on-app-permissions-for-your-microphone-in-windows).

## Confirmación y corrección en la Fase 2

El sondeo en juego recibió 115 paquetes en 1,15 s a 48 kHz y dos canales. La única discontinuidad ocurrió en el primer paquete. El búfer conserva ese primer paquete y descarta una toma interrumpida después del arranque. F3 separa duración pulsada, audio recibido, señal, discontinuidades y motivos de descarte.

El recorrido de integración alimentó ese mismo búfer con audio sintético y reprodujo la marca al inicio. Whisper Base interpretó la orden, y Unreal ejecutó o rechazó según el alcance. Las comprobaciones con voz humana y Play In Editor siguen pendientes. [Informe Fase 2](FASE_2_VOZ.md) · [Registros de Unreal](fase2/casos-ue.json).
