package com.example.crashdemo

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.crashdemo.ui.theme.CrashDemoTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CrashDemoTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    CrashTriggerScreen()
                }
            }
        }
    }
}

@Composable
fun CrashTriggerScreen() {
    Column(
        modifier = Modifier
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("CrashDemo", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(4.dp))

        Text("v1.0 Issues (existing)", style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.outline)

        Button(onClick = { triggerNPE() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger NPE (CRASH)")
        }
        Button(onClick = { triggerIndexError() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger IndexOutOfBounds (CRASH)")
        }
        Button(onClick = { triggerANR() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger ANR — UI thread sleep")
        }

        Spacer(modifier = Modifier.height(8.dp))
        HorizontalDivider()
        Spacer(modifier = Modifier.height(8.dp))

        Text("v1.1 Issues (fresh)", style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.outline)

        Button(onClick = { triggerIllegalState() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger IllegalState (CRASH)")
        }
        Button(onClick = { triggerNetworkOnMain() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger NetworkOnMain (CRASH)")
        }
        Button(onClick = { triggerDeadlockANR() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger Deadlock ANR")
        }
    }
}

// v1.0 crashes
fun triggerNPE() {
    val s: String? = null
    s!!.length
}

fun triggerIndexError() {
    listOf<Int>()[99]
}

fun triggerANR() {
    Thread.sleep(8000)  // blocks UI thread → ANR after 5s
}

// v1.1 crashes
fun triggerIllegalState() {
    check(false) { "PlayerManager failed to initialize" }
}

fun triggerNetworkOnMain() {
    java.net.URL("http://example.com").readText()  // NetworkOnMainThreadException
}

fun triggerDeadlockANR() {
    val lockA = Any()
    val lockB = Any()
    val thread = Thread {
        synchronized(lockB) {
            Thread.sleep(50)
            synchronized(lockA) { /* deadlock */ }
        }
    }
    thread.start()
    synchronized(lockA) {
        Thread.sleep(50)
        synchronized(lockB) { /* deadlock */ }
    }
}
