plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "kr.ac.u1.askcampus"
    compileSdk = 35

    defaultConfig {
        applicationId = "kr.ac.u1.askcampus"
        minSdk = 26          // Android 8.0 이상 (AVL-002)
        targetSdk = 35
        versionCode = 1
        versionName = "0.1-mvp"
        // 에뮬레이터에서 PC의 서버(localhost:8000)는 10.0.2.2로 접속한다. 앱 설정에서 바꿀 수 있음
        buildConfigField("String", "DEFAULT_SERVER", "\"http://10.0.2.2:8000/\"")
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }
    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
