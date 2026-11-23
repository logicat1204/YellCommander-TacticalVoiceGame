#pragma once

#include "AudioCaptureCore.h"
#include "CoreMinimal.h"

enum class EYellVoiceResult : uint8
{
	Ready, OpenFailed, StartFailed, NoSamples, TooShort, NoSignal, Discontinuity, InvalidFormat,
	FocusLost, TimeLimit, Interrupted
};

struct FYellVoiceStats
{
	int32 Rate = 0;
	int32 Channels = 0;
	int32 Packets = 0;
	int32 Frames = 0;
	int32 Gaps = 0;
	int32 Peak = 0;
	bool bInitialGap = false;
	bool bInvalidFormat = false;
	bool bExceededLimit = false;

	double AudioMs() const { return Rate > 0 ? 1000.0 * Frames / Rate : 0.0; }
	double PeakDbfs() const;
	EYellVoiceResult Result() const;
};

struct FYellVoiceTake
{
	FYellVoiceStats Stats;
	TArray<uint8> Wave;
};

// The device callback and game thread share only this buffer. Closing the device
// joins the capture worker before the game thread consumes the completed take.
class FYellVoiceBuffer
{
public:
	static constexpr int32 MaxSeconds = 12;
	static constexpr int32 MinMilliseconds = 250;

	void Append(const void* Audio, int32 Frames, int32 Channels, int32 Rate, bool bDiscontinuity);
	FYellVoiceStats Snapshot() const;
	FYellVoiceTake Finish(bool bBuildWave = true);

private:
	mutable FCriticalSection Lock;
	FYellVoiceStats Stats;
	TArray<int16> Pcm;
};

class FYellVoiceDevice
{
public:
	~FYellVoiceDevice();
	EYellVoiceResult Start();
	void Close();
	const FString& GetDeviceName() const { return DeviceName; }
	FYellVoiceStats Snapshot() const { return Buffer->Snapshot(); }
	FYellVoiceTake Finish(bool bBuildWave = true);

private:
	Audio::FAudioCapture Capture;
	TSharedRef<FYellVoiceBuffer, ESPMode::ThreadSafe> Buffer = MakeShared<FYellVoiceBuffer, ESPMode::ThreadSafe>();
	FString DeviceName = TEXT("Entrada predeterminada");
};

const TCHAR* YellVoiceCode(EYellVoiceResult Result);
const TCHAR* YellVoiceMessage(EYellVoiceResult Result);
