#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "YellRoundVisual.generated.h"

UCLASS()
class AYellRoundVisual : public AActor
{
	GENERATED_BODY()

public:
	AYellRoundVisual();
	void TravelTo(const FVector& Impact);
	virtual void Tick(float DeltaSeconds) override;

private:
	UPROPERTY() TObjectPtr<class UStaticMeshComponent> RoundMesh;
	FVector Destination = FVector::ZeroVector;
};
