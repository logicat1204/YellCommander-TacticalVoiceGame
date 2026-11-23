#include "YellVoice.h"

#include "Misc/ScopeLock.h"
#include "Serialization/MemoryWriter.h"

namespace
{
	constexpr int32 MinimumPeak = 12;

	TArray<uint8> MakeWave(TArray<int16>& Pcm, const int32 SampleRate)
	{
		TArray<uint8> Bytes;
		FMemoryWriter Writer(Bytes, true);
		auto Chunk = [&Writer](const ANSICHAR* Id) { Writer.Serialize(const_cast<ANSICHAR*>(Id), 4); };
		uint32 Size = Pcm.Num() * sizeof(int16);
		uint32 RiffSize = Size + 36, FormatSize = 16, Rate = SampleRate, BytesPerSecond = Rate * 2;
		uint16 Format = 1, Mono = 1, BlockAlign = 2, Bits = 16;
		Chunk("RIFF");
		Writer << RiffSize;
		Chunk("WAVE");
		Chunk("fmt ");
		Writer << FormatSize << Format << Mono << Rate << BytesPerSecond << BlockAlign << Bits;
		Chunk("data");
		Writer << Size;
		Writer.Serialize(Pcm.GetData(), Size);
		return Bytes;
	}
}

double FYellVoiceStats::PeakDbfs() const
{
	return Peak > 0 ? 20.0 * FMath::LogX(10.0, Peak / 32768.0) : -96.0;
}

EYellVoiceResult FYellVoiceStats::Result() const
{
	if (bInvalidFormat) return EYellVoiceResult::InvalidFormat;
	if (bExceededLimit) return EYellVoiceResult::TimeLimit;
	if (Gaps > (bInitialGap ? 1 : 0)) return EYellVoiceResult::Discontinuity;
	if (Frames == 0) return EYellVoiceResult::NoSamples;
	if (AudioMs() < FYellVoiceBuffer::MinMilliseconds) return EYellVoiceResult::TooShort;
	if (Peak < MinimumPeak) return EYellVoiceResult::NoSignal;
	return EYellVoiceResult::Ready;
}

void FYellVoiceBuffer::Append(const void* Audio, const int32 Frames, const int32 Channels, const int32 Rate,
	const bool bDiscontinuity)
{
	FScopeLock Guard(&Lock);
	if (Frames == 0 && !bDiscontinuity)
	{
		return;
	}
	++Stats.Packets;
	if (bDiscontinuity)
	{
		++Stats.Gaps;
		// WASAPI can mark the first packet on transition into the capture state.
		// Its samples are still useful. Later marks can remove meaningful speech.
		Stats.bInitialGap |= Stats.Packets == 1;
	}
	if (!Audio || Frames <= 0 || Channels < 1 || Channels > 32 || Rate < 8000 || Rate > 96000
		|| (Stats.Rate != 0 && (Rate != Stats.Rate || Channels != Stats.Channels)))
	{
		Stats.bInvalidFormat = true;
		return;
	}
	Stats.Rate = Rate;
	Stats.Channels = Channels;
	const int32 Count = FMath::Min(Frames, Rate * MaxSeconds - Pcm.Num());
	Stats.bExceededLimit |= Count < Frames;
	const float* Source = static_cast<const float*>(Audio);
	for (int32 Frame = 0; Frame < Count; ++Frame)
	{
		double Sum = 0;
		for (int32 Channel = 0; Channel < Channels; ++Channel)
		{
			const float Sample = Source[Frame * Channels + Channel];
			if (!FMath::IsFinite(Sample))
			{
				Stats.bInvalidFormat = true;
				return;
			}
			Sum += FMath::Clamp(Sample, -1.0f, 1.0f);
		}
		const int16 Sample = static_cast<int16>((Sum / Channels) * 32767.0);
		Pcm.Add(Sample);
		Stats.Peak = FMath::Max(Stats.Peak, FMath::Abs(static_cast<int32>(Sample)));
	}
	Stats.Frames = Pcm.Num();
}

FYellVoiceStats FYellVoiceBuffer::Snapshot() const
{
	FScopeLock Guard(&Lock);
	return Stats;
}

FYellVoiceTake FYellVoiceBuffer::Finish(const bool bBuildWave)
{
	FScopeLock Guard(&Lock);
	FYellVoiceTake Take;
	Take.Stats = Stats;
	if (bBuildWave && Stats.Result() == EYellVoiceResult::Ready)
	{
		Take.Wave = MakeWave(Pcm, Stats.Rate);
	}
	Pcm.Reset();
	Stats = {};
	return Take;
}

FYellVoiceDevice::~FYellVoiceDevice()
{
	Close();
}

EYellVoiceResult FYellVoiceDevice::Start()
{
	Audio::FCaptureDeviceInfo Info;
	if (Capture.GetCaptureDeviceInfo(Info))
	{
		DeviceName = MoveTemp(Info.DeviceName);
	}
	Audio::FAudioCaptureDeviceParams Params;
	Params.PCMAudioEncoding = Audio::EPCMAudioEncoding::FLOATING_POINT_32;
	if (!Capture.OpenAudioCaptureStream(Params,
		[Target = Buffer](const void* Audio, int32 Frames, int32 Channels, int32 Rate, double, bool bGap)
		{
			Target->Append(Audio, Frames, Channels, Rate, bGap);
		}, 1024))
	{
		return EYellVoiceResult::OpenFailed;
	}
	if (!Capture.StartStream())
	{
		Close();
		return EYellVoiceResult::StartFailed;
	}
	return EYellVoiceResult::Ready;
}

void FYellVoiceDevice::Close()
{
	if (Capture.IsCapturing())
	{
		Capture.StopStream();
	}
	if (Capture.IsStreamOpen())
	{
		Capture.CloseStream();
	}
}

FYellVoiceTake FYellVoiceDevice::Finish(const bool bBuildWave)
{
	Close();
	return Buffer->Finish(bBuildWave);
}

const TCHAR* YellVoiceCode(const EYellVoiceResult Result)
{
	switch (Result)
	{
	case EYellVoiceResult::Ready: return TEXT("listo");
	case EYellVoiceResult::OpenFailed: return TEXT("dispositivo_no_disponible");
	case EYellVoiceResult::StartFailed: return TEXT("dispositivo_no_inicia");
	case EYellVoiceResult::NoSamples: return TEXT("sin_muestras");
	case EYellVoiceResult::TooShort: return TEXT("duracion_insuficiente");
	case EYellVoiceResult::NoSignal: return TEXT("sin_senal");
	case EYellVoiceResult::Discontinuity: return TEXT("corte_durante_captura");
	case EYellVoiceResult::InvalidFormat: return TEXT("formato_invalido");
	case EYellVoiceResult::FocusLost: return TEXT("foco_perdido");
	case EYellVoiceResult::TimeLimit: return TEXT("limite_de_tiempo");
	default: return TEXT("captura_cancelada");
	}
}

const TCHAR* YellVoiceMessage(const EYellVoiceResult Result)
{
	switch (Result)
	{
	case EYellVoiceResult::OpenFailed: return TEXT("No se pudo abrir el micrófono. Revisa la entrada de Windows.");
	case EYellVoiceResult::StartFailed: return TEXT("El micrófono abrió, pero no inició la captura.");
	case EYellVoiceResult::NoSamples: return TEXT("El micrófono no entregó muestras. Mantén V mientras hablas.");
	case EYellVoiceResult::TooShort: return TEXT("Audio de menos de 250 ms. Mantén V hasta terminar la frase.");
	case EYellVoiceResult::NoSignal: return TEXT("Sin señal del micrófono. Revisa el nivel de entrada.");
	case EYellVoiceResult::Discontinuity: return TEXT("Se cortó el audio durante la captura. Repite la orden.");
	case EYellVoiceResult::InvalidFormat: return TEXT("El formato del micrófono es inválido o cambió durante la captura.");
	case EYellVoiceResult::FocusLost: return TEXT("Captura cancelada al salir de la ventana de juego.");
	case EYellVoiceResult::TimeLimit: return TEXT("Límite de 12 s. Suelta V y repite la orden en una frase más corta.");
	default: return TEXT("La captura terminó antes de poder transmitir.");
	}
}
