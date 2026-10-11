# Android 빌드 실패: Android Studio JBR(Java 25)와 local.properties 경로 이스케이프

- **발생 시각**: 2026-10-12
- **위치**: `android/` (`gradlew.bat assembleDebug`), Gradle 8.7 / AGP 8.6.0
- **상태**: 해결됨

## 증상

1차 (JAVA_HOME = Android Studio 내장 JBR):

```
FAILURE: Build failed with an exception.
* What went wrong:
25.0.3
```

2차 (JAVA_HOME = JDK 21):

```
Could not determine the dependencies of task ':app:compileDebugJavaWithJavac'.
> java.io.IOException: (깨진 한글) — "파일 이름, 디렉터리 이름 또는 볼륨 레이블 구문이 잘못되었습니다"
```

## 원인 조사

- 1차: 메시지가 버전 문자열 `25.0.3`뿐이었다. 이 PC의 Android Studio 내장 JBR이 Java 25이고, Gradle 8.7은 Java 25를 실행 환경으로 인식하지 못한다. 시스템에 설치된 JDK 21(`C:\Program Files\Java\jdk-21.0.12.1`)로 바꾸자 이 오류는 사라졌다.
- 2차: Windows의 "잘못된 파일 이름" 오류. `local.properties`를 `printf`로 만들면서 `sdk.dir=C\:\Users\...`처럼 백슬래시가 한 번만 들어갔다. properties 형식에서 `\U`, `\s` 등이 이스케이프로 처리되어 경로가 깨졌다.

## 근본 원인

1. 빌드 JDK가 Gradle 8.7이 지원하지 않는 Java 25였다.
2. `local.properties`의 SDK 경로가 잘못 이스케이프되었다.

## 해결 방법

- 빌드할 때 `JAVA_HOME`을 JDK 21로 지정한다.
- `local.properties`를 `sdk.dir=C:/Users/ssh96/AppData/Local/Android/Sdk`(슬래시)로 다시 썼다.
- `kotlin { jvmToolchain(17) }`은 JDK 17을 따로 요구하므로 쓰지 않고, `jvmTarget = 17`만 지정했다.
- 결과: `BUILD SUCCESSFUL`, `app-debug.apk` 6.3MB.

## 재발 방지

- README의 빌드 명령에 JDK 21을 쓰도록 적었다. Android Studio로 열 때도 Gradle JDK를 JDK 17~21로 고른다.
- `local.properties`는 PC마다 다르므로 git에 올리지 않는다 (`android/.gitignore`). Android Studio로 처음 열면 자동으로 만들어진다.
