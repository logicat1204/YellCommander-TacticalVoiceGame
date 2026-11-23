// OvDataRows.h  - Estructuras de fila para importar los CSV como DataTable (UE5)
// Copiar a Source/<TuModulo>/Data/ y compilar. Al importar cada CSV elegir la estructura indicada.
#pragma once
#include "CoreMinimal.h"
#include "Engine/DataTable.h"
#include "GameplayTagContainer.h"
#include "OvDataRows.generated.h"

USTRUCT(BlueprintType) struct FZonaRow : public FTableRowBase { GENERATED_BODY()   // DT_Zonas.csv
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FGameplayTag ZonaTag;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString NombreES;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Alias;        // separados por ';'
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector Ubicacion;    // uu, Landscape en (0,0,0)
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Radio = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Rol; };

USTRUCT(BlueprintType) struct FComandoRow : public FTableRowBase { GENERATED_BODY() // DT_Comandos.csv
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FGameplayTag ComandoTag;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool RequiereObjetivo = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool RequiereUnidadDestino = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Prioridad = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Ejemplo; };

USTRUCT(BlueprintType) struct FUnidadRow : public FTableRowBase { GENERATED_BODY()  // DT_Unidades.csv
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString NombreES;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Rol;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Escuadron;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 NumMiembros = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float VidaMax = 100.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float VelCaminar = 200.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float VelCorrer = 450.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float VelAgachado = 120.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float AlcanceDisparo = 4500.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float DanoDisparo = 10.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float CadenciaSeg = 0.2f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Alias; };

USTRUCT(BlueprintType) struct FOleadaRow : public FTableRowBase { GENERATED_BODY()  // DT_Oleadas.csv
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Oleada = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float InicioSeg = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName ZonaSpawn;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 NumFusileros = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float IntervaloSeg = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName ZonaObjetivo;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Nota; };

USTRUCT(BlueprintType) struct FReplicaRow : public FTableRowBase { GENERATED_BODY()  // DT_Replicas.csv
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Categoria;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Texto;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftObjectPtr<USoundBase> Sonido; };
